# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import asyncio
from cortx.utils.log import Log
from cortx.utils.product_features import unsupported_features
from csm.common.payload import Json
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const


class PostInstall(Setup):
    """
     Perform post-install for csm
            : Configure csm user
            : Add Permission for csm user
        Post install is used after just all rpms are install but
        no services are started.
    """

    def __init__(self):
        Log.info("Triggering csm_setup post_install")
        super(PostInstall, self).__init__()

    def execute(self):
        """
        Execute And Process Csm Post Install Steps.
        :return:
        """
        try:
            self._config_user()
            self.set_unsupported_feature_info()
            self._configure_system_auto_restart()
        except Exception as e:
            import traceback
            Log.error((f"csm_setup post_install failed. Error: {e} - "
                       f"{str(traceback.format_exc())}"))
            raise CsmSetupError(f"csm_setup post_install failed. Error: {e}.")

    def _config_user(self):
        """
        Check user already exist and create if not exist
        If reset true then delete user
        """
        Log.info("Check user already exist and create if not exist.")
        if not self._is_user_exist():
            Setup._run_cmd((f"useradd -d {const.CSM_USER_HOME} -p"
                            f" {self._password} {self._user}"))
            Setup._run_cmd(f"usermod -aG wheel {self._user}")
            if not self._is_user_exist():
                raise CsmSetupError(f"Unable to create %s user {self._user}")

        if self._is_user_exist() and Setup._is_group_exist(
                const.HA_CLIENT_GROUP):
            Setup._run_cmd(
                f"usermod -a -G {const.HA_CLIENT_GROUP}  {self._user}")

    def set_unsupported_feature_info(self):
        """
        This method stores CSM unsupported features in two ways:
        1. It first gets all the unsupported features lists of the components,
        which CSM interacts with. Add all these features as CSM unsupported
        features. The list of components, CSM interacts with, is
        stored in csm.conf file. So if there is change in name of any
        component, csm.conf file must be updated accordingly.
        2. Installation/envioronment type and its mapping with CSM unsupported
        features are maintained in unsupported_feature_schema. Based on the
        installation/environment type received as argument, CSM unsupported
        features can be stored.
        """

        def get_component_list_from_features_endpoints():
            feature_endpoints = Json(
                const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
            component_list = [feature for v in feature_endpoints.values()
                  for feature in v.get(const.DEPENDENT_ON)]
            return list(set(component_list))

        try:
            Log.info("Set unsupported feature list to ES")
            self._setup_info = self.get_data_from_provisioner_cli(
                const.GET_SETUP_INFO)
            unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
            _loop = asyncio.get_event_loop()
            components_list = get_component_list_from_features_endpoints()
            unsupported_features_list = []
            for component in components_list:
                unsupported = _loop.run_until_complete(
                    unsupported_feature_instance.get_unsupported_features(
                        component_name=component))
                for feature in unsupported:
                    unsupported_features_list.append(
                        feature.get(const.FEATURE_NAME))
            csm_unsupported_feature = Json(
                const.UNSUPPORTED_FEATURE_SCHEMA).load()
            for setup in csm_unsupported_feature[const.SETUP_TYPES]:
                if setup[const.NAME] == self._setup_info[const.STORAGE_TYPE]:
                    unsupported_features_list.extend(
                        setup[const.UNSUPPORTED_FEATURES])
            unsupported_features_list = list(set(unsupported_features_list))
            unique_unsupported_features_list = list(
                filter(None, unsupported_features_list))
            if unique_unsupported_features_list:

                _loop.run_until_complete(
                    unsupported_feature_instance.store_unsupported_features(
                    component_name=str(const.CSM_COMPONENT_NAME),
                        features=unique_unsupported_features_list))
            else:
                Log.info("Unsupported features list is empty.")
        except Exception as e_:
            Log.error(f"Error in storing unsupported features: {e_}")

    def _configure_system_auto_restart(self):
        """
        Check's System Installation Type an dUpdate the Service File
        Accordingly.
        :return: None
        """
        Log.info("Configuring System Auto restart")
        is_auto_restart_required = list()
        if self._setup_info:
            for each_key in self._setup_info:
                comparison_data = const.EDGE_INSTALL_TYPE.get(each_key, None)
                # Check Key Exists:
                if comparison_data is None:
                    Log.warn(f"Edge Installation missing key {each_key}")
                    continue
                if isinstance(comparison_data, list):
                    if self._setup_info[each_key] in comparison_data:
                        is_auto_restart_required.append(False)
                    else:
                        is_auto_restart_required.append(True)
                elif self._setup_info[each_key] == comparison_data:
                    is_auto_restart_required.append(False)
                else:
                    is_auto_restart_required.append(True)
        else:
            Log.warn("Setup info does not exist.")
            is_auto_restart_required.append(True)
        if any(is_auto_restart_required):
            Log.debug("Updating All setup file for Auto Restart on "
                      "Failure")
            Setup._update_service_file("#< RESTART_OPTION >",
                                       "Restart=on-failure")
            Setup._run_cmd("systemctl daemon-reload")
