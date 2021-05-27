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


import crypt
import os
from cortx.utils.log import Log
from cortx.utils.product_features import unsupported_features
from cortx.utils.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_pkg import PkgV
from csm.common.payload import Json
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.payload import Text
from cortx.utils.service.service_handler import Service

class PostInstall(Setup):
    """
    Perform post-install for csm
        : Configure csm user
        : Add Permission for csm user
    Post install is used after just all rpms are install but
    no service are started
    """

    def __init__(self):
        """Instiatiate Post Install Class."""
        Log.info("Executing Post Installation for CSM.")
        super(PostInstall, self).__init__()

    async def execute(self, command):
        """
        Execute all the Methods Required for Post Install Steps of CSM Rpm's.
        :param command: Command Class Object :type: class
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(
                const.CONFIG_URL))
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")
        self._prepare_and_validate_confstore_keys()
        self._set_deployment_mode()
        self.validate_3rd_party_pkgs()
        self._config_user()
        self._configure_system_auto_restart()
        self._configure_service_user()
        self._configure_rsyslog()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SERVER_NODE_INFO:f"{const.SERVER_NODE_INFO}",
            const.KEY_SERVER_NODE_TYPE:f"{const.SERVER_NODE_INFO}>{const.TYPE}",
            const.KEY_ENCLOSURE_ID:f"{const.SERVER_NODE_INFO}>{const.STORAGE}>{const.ENCLOSURE_ID}",
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}"
            })
        try:
            self._validate_conf_store_keys(const.CONSUMER_INDEX)
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def validate_3rd_party_pkgs(self):
        try:
            Log.info("Validating third party rpms")
            PkgV().validate("rpms", const.third_party_rpms)
            Log.info("Valdating  3rd party Python Packages")
            PkgV().validate("pip3s", self.fetch_python_pkgs())
        except VError as ve:
            Log.error(f"Failed at package Validation: {ve}")
            raise CsmSetupError(f"Failed at package Validation: {ve}")

    def fetch_python_pkgs(self):
        try:
            pkgs_data = Text(const.python_pkgs_req_path).load()
            return {ele.split("==")[0]:ele.split("==")[1] for ele in pkgs_data.splitlines()}
        except Exception as e:
            Log.error(f"Failed to fetch python packages: {e}")
            raise CsmSetupError("Failed to fetch python packages")

    def _config_user(self, reset=False):
        """
        Check user already exist and create if not exist
        If reset true then delete user
        """
        if not self._is_user_exist():
            Log.info("Creating CSM User without password.")
            Setup._run_cmd((f"useradd -M {self._user}"))
            Log.info("Adding CSM User to Wheel Group.")
            Setup._run_cmd(f"usermod -aG wheel {self._user}")
            Log.info("Enabling nologin for CSM user.")
            Setup._run_cmd(f"usermod -s /sbin/nologin {self._user}")
            if not self._is_user_exist():
                Log.error("Csm User Creation Failed.")
                raise CsmSetupError(f"Unable to create {self._user} user")
        else:
            Log.info(f"User {self._user} already exist")

        if self._is_user_exist() and Setup._is_group_exist(
                const.HA_CLIENT_GROUP):
            Log.info(f"Add Csm User: {self._user} to HA-Client Group.")
            Setup._run_cmd(
                f"usermod -a -G {const.HA_CLIENT_GROUP} {self._user}")

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
                comparison_data = const.EDGE_INSTALL_TYPE.get(each_key,
                                                              None)
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

    def _configure_service_user(self):
        """
        Configures the Service user in CSM service files.
        :return:
        """
        Setup._update_service_file("<USER>", self._user)

    def _configure_rsyslog(self):
        """
        Configure rsyslog
        """
        Log.info("Configuring rsyslog")
        os.makedirs(const.RSYSLOG_DIR, exist_ok=True)
        if os.path.exists(const.RSYSLOG_DIR):
            Setup._run_cmd(f"cp -f {const.SOURCE_RSYSLOG_PATH} {const.RSYSLOG_PATH}")
            Log.info("Restarting rsyslog service")
            service_obj = Service('rsyslog.service')
            service_obj.restart()
        else:
            msg = f"rsyslog failed. {const.RSYSLOG_DIR} directory missing."
            Log.error(msg)
            raise CsmSetupError(msg)