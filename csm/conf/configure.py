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

import os
import time
from cortx.utils.product_features import unsupported_features
from marshmallow.exceptions import ValidationError
from csm.common.payload import Json
from csm.common.service_urls import ServiceUrls
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.message_bus import MessageBusAdmin,MessageBus


class Configure(Setup):
    """
    Perform configuration for csm
        : Move conf file to etc
    Config is used to move update conf files one time configuration
    """
    def __init__(self):
        super(Configure, self).__init__()
        Log.info("Triggering csm_setup config")
        self._replacement_node_flag = os.environ.get(
            "REPLACEMENT_NODE") == "true"
        if self._replacement_node_flag:
            Log.info("REPLACEMENT_NODE flag is set")

    async def execute(self, command):
        """
        Execute csm_setup config operation.

        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Setup.load_csm_config_indices()
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        self.force_action = command.options.get('f')
        Log.info(f"Force flag: {self.force_action}")
        services = command.options.get("services")
        if ',' in services:
            services = services.split(",")
        elif 'all' in services:
            services = ["agent"]
        else:
            services=[services]
        if not "agent" in services:
            return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
        self._prepare_and_validate_confstore_keys()

        self.cluster_id = Conf.get(const.CONSUMER_INDEX,
                        self.conf_store_keys[const.KEY_CLUSTER_ID])
        Configure._set_csm_endpoint()
        Configure._set_s3_info()
        Configure.set_hax_endpoint()
        Configure._create_topics()
        try:
            await self._create_cluster_admin(self.force_action)
            self.create()
            for count in range(0, 4):
                try:
                    await self._set_unsupported_feature_info()
                    break
                except Exception as e_:
                    Log.warn(f"Unable to connect to ES. Retrying : {count+1}. {e_}")
                    time.sleep(2**count)
        except ValidationError as ve:
            Log.error(f"Validation Error: {ve}")
            raise CsmSetupError(f"Validation Error: {ve}")
        except Exception as e:
            import traceback
            err_msg = (f"csm_setup config command failed. Error: "
                       f"{e} - {str(traceback.format_exc())}")
            Log.error(err_msg)
            raise CsmSetupError(err_msg)
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
                const.KEY_SERVER_NODE_INFO:f"{const.NODE}>{self.machine_id}",
                const.KEY_CLUSTER_ID:f"{const.NODE}>{self.machine_id}>{const.CLUSTER_ID}",
                const.CSM_AGENT_ENDPOINTS:f"{const.CSM_AGENT_ENDPOINTS_KEY}",
                const.RGW_S3_DATA_ENDPOINT: f"{const.RGW_S3_DATA_ENDPOINTS_KEY}",
                const.RGW_S3_AUTH_USER: f"{const.RGW_S3_AUTH_USER_KEY}",
                const.RGW_S3_AUTH_ADMIN: f"{const.RGW_S3_AUTH_ADMIN_KEY}",
                const.RGW_S3_AUTH_SECRET: f"{const.RGW_S3_AUTH_SECRET_KEY}"
                })

        Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)

    @staticmethod
    def _set_csm_endpoint():
        Log.info("Setting csm endpoint in csm config")
        csm_endpoint = Conf.get(const.CONSUMER_INDEX, const.CSM_AGENT_ENDPOINTS_KEY)
        csm_protocol, csm_host, csm_port = ServiceUrls.parse_url(csm_endpoint)
        Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_ENDPOINTS, csm_endpoint)
        # Not considering Hostname. Bydefault 0.0.0.0 used
        # Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_HOST, csm_host)
        if csm_protocol == 'https':
            Conf.set(const.CSM_GLOBAL_INDEX, const.CSM_DEBUG_MODE, 'false')
        else:
            Conf.set(const.CSM_GLOBAL_INDEX, const.CSM_DEBUG_MODE, 'true')
        Conf.set(const.CSM_GLOBAL_INDEX, const.HTTPS_PORT, csm_port)
        Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_PORT, csm_port)
        Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_BASE_URL, csm_protocol+'://')

    @staticmethod
    def _set_s3_endpoints():
        s3_endpoints = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_DATA_ENDPOINTS_KEY)
        if s3_endpoints:
            Log.info(f"Fetching s3 endpoint.{s3_endpoints}")
            s3_endpoints_count = len(s3_endpoints)
            for endpoint_count in range(s3_endpoints_count):
                Conf.set(const.CSM_GLOBAL_INDEX,
                        f'{const.RGW_S3_ENDPOINTS}[{endpoint_count}]',
                        eval(f'{s3_endpoints}[{endpoint_count}]'))
        else:
            raise CsmSetupError("S3 endpoints not found.")

    @staticmethod
    def _set_s3_info():
        """
        This Function will set s3  related configurations.
        :return:
        """
        Log.info("Setting S3 configurations in csm config")
        Configure._set_s3_endpoints()
        # Set IAM user credentails
        s3_auth_user = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_AUTH_USER_KEY)
        s3_auth_admin = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_AUTH_ADMIN_KEY)
        s3_auth_secret = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_AUTH_SECRET_KEY)
        Conf.set(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ADMIN_USER, s3_auth_user)
        Conf.set(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ACCESS_KEY, s3_auth_admin)
        Conf.set(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_SECRET_KEY, s3_auth_secret)

    @staticmethod
    def _get_hax_endpoint(endpoints):
        for endpoint in endpoints:
            protocol, _, _ = ServiceUrls.parse_url(endpoint)
            if protocol == "https" or protocol == "http":
                return endpoint

    @staticmethod
    def set_hax_endpoint():
        endpoints = Conf.get(const.CONSUMER_INDEX, const.HAX_ENDPOINT_KEY)
        hax_endpoint = Configure._get_hax_endpoint(endpoints)
        Conf.set(const.CSM_GLOBAL_INDEX, const.CAPACITY_MANAGMENT_HCTL_SVC_ENDPOINT,
                hax_endpoint)

    async def _set_unsupported_feature_info(self):
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
            Log.info("Get Component List.")
            feature_endpoints = Json(
                const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
            component_list = [feature for v in feature_endpoints.values() for
                              feature in v.get(const.DEPENDENT_ON)]
            return list(set(component_list))
        try:
            Log.info("Set unsupported feature list to ES.")
            unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
            components_list = get_component_list_from_features_endpoints()
            unsupported_features_list = []
            for component in components_list:
                Log.info(f"Fetch Unsupported Features for {component}.")
                unsupported = await unsupported_feature_instance.get_unsupported_features(
                    component_name=component)
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
                Log.info("Store Unsupported Features.")
                await unsupported_feature_instance.store_unsupported_features(
                    component_name=str(const.CSM_COMPONENT_NAME),
                    features=unique_unsupported_features_list)
            else:
                Log.info("Unsupported features list is empty.")
        except Exception as e_:
            Log.error(f"Error in storing unsupported features: {e_}")
            raise CsmSetupError(f"Error in storing unsupported features: {e_}")

    @staticmethod
    def _create_perf_stat_topic(mb_admin):
        message_type = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_MSG_TYPE)
        partitions = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_PARTITIONS))
        retention_size = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_RETENTION_SIZE))
        retention_period = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_RETENTION_PERIOD))
        if not message_type in mb_admin.list_message_types():
            Log.info(f"Registering message_type:{message_type}")
            mb_admin.register_message_type(message_types=[message_type], partitions=partitions)
            mb_admin.set_message_type_expire(message_type,
                                            expire_time_ms=retention_period,
                                            data_limit_bytes=retention_size)
        else:
            Log.info(f"message_type:{message_type} already exists.")
    
    @staticmethod
    def _create_cluster_stop_topic(mb_admin):
        message_type = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_MSG_TYPE)
        partitions = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_PARTITIONS))
        retention_size = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_RETENTION_SIZE))
        retention_period = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_RETENTION_PERIOD))
        if not message_type in mb_admin.list_message_types():
            Log.info(f"Registering message_type:{message_type}")
            mb_admin.register_message_type(message_types=[message_type], partitions=partitions)
            mb_admin.set_message_type_expire(message_type,
                                            expire_time_ms=retention_period,
                                            data_limit_bytes=retention_size)
    @staticmethod
    def _create_topics():
        """
        Create required messagebus topics for csm.
        """
        message_server_endpoints = Conf.get(const.CONSUMER_INDEX, const.KAFKA_ENDPOINTS)
        MessageBus.init(message_server_endpoints)
        mb_admin = MessageBusAdmin(admin_id = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_ADMIN_ID))
        Configure._create_perf_stat_topic(mb_admin)
        Configure._create_cluster_stop_topic(mb_admin)
