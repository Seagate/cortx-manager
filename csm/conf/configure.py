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
# from cortx.utils.product_features import unsupported_features
from marshmallow.exceptions import ValidationError
from csm.common.service_urls import ServiceUrls
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.message_bus import MessageBusAdmin,MessageBus
from cortx.utils.message_bus.error import MessageBusError
from csm.common.utility import Utility
from cortx.utils.validator.error import VError


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
            conf = command.options.get(const.CONFIG_URL)
            Utility.load_csm_config_indices(conf)
            Setup.setup_logs_init()
            Log.info("Setup: Initiating Config phase.")
        except (KvError, VError) as e:
            Log.error(f"Config: Configuration loading failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        self.force_action = command.options.get('f')
        Log.info(f"Config: Force flag: {self.force_action}")
        services = command.options.get("services")
        if ',' in services:
            services = services.split(",")
        elif 'all' in services:
            services = ["agent"]
        else:
            services=[services]
        if "agent" not in services:
            return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
        self._prepare_and_validate_confstore_keys()

        self.cluster_id = Conf.get(const.CONSUMER_INDEX,
                        self.conf_store_keys[const.KEY_CLUSTER_ID])
        Configure.set_resource_limits()
        Configure._set_csm_endpoint()
        Configure._set_s3_info()
        Configure.set_hax_endpoint()

        try:
            Log.info("Config: Creating topics for various CSM functionalities.")
            Configure._create_topics()
        except MessageBusError as ex:
            Log.error(f"Config: Message bus connection error : {ex}")
            raise CsmSetupError(f"Message bus connection error : {ex}")
        except Exception as ex:
            Log.error(f"Config: Error occured while creating topics : {ex}")
            raise CsmSetupError(f"Error occured while creating topics : {ex}")

        try:
            await self._create_cluster_admin(self.force_action)
            self.create()
            # Disabled: unsupported features
            # for count in range(0, 4):
            #     try:
            #         await self._set_unsupported_feature_info()
            #         break
            #     except Exception as e_:
            #         Log.warn(f"Unable to connect to ES. Retrying : {count+1}. {e_}")
            #         time.sleep(2**count)
            # else:
            #     raise CsmSetupError("Unable to connect to storage after 4 attempts")
        except ValidationError as ve:
            Log.error(f"Config: Validation Error: {ve}")
            raise CsmSetupError(f"Validation Error: {ve}")
        except Exception as e:
            import traceback
            err_msg = (f"csm_setup config command failed. Error: "
                       f"{e} - {str(traceback.format_exc())}")
            Log.error(err_msg)
            raise CsmSetupError(err_msg)
        Log.info("Setup: Successfully passed Config phase.")
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        Log.info("Config: Validating required configuration.")
        self.conf_store_keys.update({
                const.KEY_CLUSTER_ID:f"{const.NODE}>{self.machine_id}>{const.CLUSTER_ID}",
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

        Log.info("Config: Creating CSM configuration file on required location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        try:
            Utility.validate_consul()
        except VError as e:
            Log.error(f"Unable to save the configurations to consul: {e}")
            raise CsmSetupError("Unable to save the configurations")
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)

    @staticmethod
    def _set_csm_endpoint():
        Log.info("Config: Setting CSM endpoint in configuration.")
        csm_endpoint = Conf.get(const.CONSUMER_INDEX, const.CSM_AGENT_ENDPOINTS_KEY)
        csm_protocol, _, csm_port = ServiceUrls.parse_url(csm_endpoint)
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
        Log.info("Config: Setting S3 endpoints in configuration")
        result : bool = False
        count_endpoints : str = Conf.get(const.CONSUMER_INDEX,
            const.RGW_NUM_ENDPOINTS_KEY)
        try:
            count_endpoints = int(count_endpoints)
        except ValueError:
            raise CsmSetupError("Rgw num_endpoints value is not a valid"
                " integer.")
        for count in range(count_endpoints):
            endpoint = Conf.get(const.CONSUMER_INDEX,
                f'{const.RGW_S3_DATA_ENDPOINTS_KEY}[{count}]')
            if endpoint:
                result = True
                Conf.set(const.CSM_GLOBAL_INDEX,
                        f'{const.RGW_S3_ENDPOINTS}[{count}]', endpoint)
        if not result:
            raise CsmSetupError("S3 endpoint not found.")

    @staticmethod
    def _set_s3_info():
        """
        This Function will set s3  related configurations.
        :return:
        """
        Log.info("Config: Setting S3 information in configuration")
        Configure._set_s3_endpoints()
        # Set IAM user credentails
        s3_auth_user = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_AUTH_USER_KEY)
        s3_auth_admin = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_AUTH_ADMIN_KEY)
        s3_auth_secret = Conf.get(const.CONSUMER_INDEX, const.RGW_S3_AUTH_SECRET_KEY)
        Conf.set(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ADMIN_USER, s3_auth_user)
        Conf.set(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ACCESS_KEY, s3_auth_admin)
        Conf.set(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_SECRET_KEY, s3_auth_secret)

    @staticmethod
    def set_hax_endpoint():
        Log.info("Config: Setting HAX endpoints in configuration")
        hax_endpoint = None
        result : bool = False
        count_endpoints : str = Conf.get(const.CONSUMER_INDEX,
            const.HAX_NUM_ENDPOINT_KEY)
        try:
            count_endpoints = int(count_endpoints)
        except ValueError:
            raise CsmSetupError("Hax num_endpoints value is not a valid"
                " integer.")
        for count in range(int(count_endpoints)):
            endpoint = Conf.get(const.CONSUMER_INDEX,
                f'{const.HAX_ENDPOINT_KEY}[{count}]')
            if endpoint:
                protocol, _, _ = ServiceUrls.parse_url(endpoint)
                if protocol == "https" or protocol == "http":
                    result = True
                    hax_endpoint = endpoint
                    break
        if not result:
            raise CsmSetupError("Hax endpoint not found.")
        Conf.set(const.CSM_GLOBAL_INDEX, const.CAPACITY_MANAGMENT_HCTL_SVC_ENDPOINT,
                hax_endpoint)

    # async def _set_unsupported_feature_info(self):
    #     """
    #     This method stores CSM unsupported features in two ways:
    #     1. It first gets all the unsupported features lists of the components,
    #     which CSM interacts with. Add all these features as CSM unsupported
    #     features. The list of components, CSM interacts with, is
    #     stored in csm.conf file. So if there is change in name of any
    #     component, csm.conf file must be updated accordingly.
    #     2. Installation/envioronment type and its mapping with CSM unsupported
    #     features are maintained in unsupported_feature_schema. Based on the
    #     installation/environment type received as argument, CSM unsupported
    #     features can be stored.
    #     """

    #     def get_component_list_from_features_endpoints():
    #         Log.info("Config: Getting component list.")
    #         feature_endpoints = Json(
    #             const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
    #         component_list = [feature for v in feature_endpoints.values() for
    #                           feature in v.get(const.DEPENDENT_ON)]
    #         return list(set(component_list))
    #     try:
    #         Log.info("Config: Setting unsupported feature list to storage.")
    #         unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
    #         components_list = get_component_list_from_features_endpoints()
    #         unsupported_features_list = []
    #         for component in components_list:
    #             Log.info(f"Config: Fetching unsupported features for {component}.")
    #             unsupported = await unsupported_feature_instance.get_unsupported_features(
    #                 component_name=component)
    #             for feature in unsupported:
    #                 unsupported_features_list.append(
    #                     feature.get(const.FEATURE_NAME))
    #         csm_unsupported_feature = Json(
    #             const.UNSUPPORTED_FEATURE_SCHEMA).load()
    #         unsupported_features_list.extend(csm_unsupported_feature)

    #         unsupported_features_list = list(set(unsupported_features_list))
    #         unique_unsupported_features_list = list(
    #             filter(None, unsupported_features_list))
    #         if unique_unsupported_features_list:
    #             Log.info("Config: Storing unsupported features.")
    #             await unsupported_feature_instance.store_unsupported_features(
    #                 component_name=str(const.CSM_COMPONENT_NAME),
    #                 features=unique_unsupported_features_list)
    #         else:
    #             Log.info("Config: Unsupported features list is empty.")
    #     except Exception as e_:
    #         Log.error(f"Config: Error in storing unsupported features: {e_}")
    #         raise CsmSetupError(f"Error in storing unsupported features: {e_}")

    @staticmethod
    def _create_perf_stat_topic(mb_admin):
        Log.info("Config: Creating performance statistics topic")
        message_type = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_MSG_TYPE)
        partitions = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_PARTITIONS))
        retention_size = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_RETENTION_SIZE))
        retention_period = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_RETENTION_PERIOD))
        if message_type not in mb_admin.list_message_types():
            Log.info(f"Config: Registering message_type:{message_type}")
            mb_admin.register_message_type(message_types=[message_type], partitions=partitions)
            mb_admin.set_message_type_expire(message_type,
                                            expire_time_ms=retention_period,
                                            data_limit_bytes=retention_size)
        else:
            Log.info(f"Config: message_type:{message_type} already exists.")

    @staticmethod
    def _create_cluster_stop_topic(mb_admin):
        Log.info("Config: Creating cluster stop topic")
        message_type = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_MSG_TYPE)
        partitions = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_PARTITIONS))
        retention_size = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_RETENTION_SIZE))
        retention_period = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_RETENTION_PERIOD))
        if message_type not in mb_admin.list_message_types():
            Log.info(f"Config: Registering message_type:{message_type}")
            mb_admin.register_message_type(message_types=[message_type], partitions=partitions)
            mb_admin.set_message_type_expire(message_type,
                                            expire_time_ms=retention_period,
                                            data_limit_bytes=retention_size)
    @staticmethod
    def _create_topics():
        """
        Create required messagebus topics for csm.
        """
        Log.info("Config: Creating topics for communication channel.")
        result : bool = False
        message_server_endpoints = list()
        count_endpoints : str = Conf.get(const.CONSUMER_INDEX,
            const.KAFKA_NUM_ENDPOINTS)
        try:
            count_endpoints = int(count_endpoints)
        except ValueError:
            raise CsmSetupError("Kafka num_endpoints value is not a valid"
                " integer.")
        for count in range(count_endpoints):
            endpoint = Conf.get(const.CONSUMER_INDEX,
                f'{const.KAFKA_ENDPOINTS}[{count}]')
            if endpoint:
                result =  True
                message_server_endpoints.append(endpoint)
        if not result:
            raise CsmSetupError("Kafka endpoint not found.")
        Log.info(f"Config: Connecting to message bus using endpoint :{message_server_endpoints}")
        MessageBus.init(message_server_endpoints)
        mb_admin = MessageBusAdmin(admin_id = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_ADMIN_ID))
        Configure._create_perf_stat_topic(mb_admin)
        Configure._create_cluster_stop_topic(mb_admin)

    @staticmethod
    def _calculate_request_quota(mem_min: int, mem_max: int, cpu_min: int, cpu_max: int) -> int:
        """
        Calculate the maximum number of requests CSM handles at particular time.

        :param mem_min: minimum memory limit.
        :param mem_max: maximum memory limit.
        :param cpu_min: minumem CPU limit.
        :param cpu_max: maximum CPU limit.
        :returns: number of requests.
        """
        Log.info(f"CPU boundaries are currently not included in calculation: {cpu_min}:{cpu_max}")
        # Minimum memroy limit is considered the bare minimem to run CSM only.
        # The rest part up to maximum limit is for handling incoming requests.
        # CSM also reserves some amount (const.CSM_USAGE_RESERVED_BUFFER_PERCENT) for future needs.
        # MaxConcurrentRequest =  MaxAvailableMemForRequest/RequestSize

        reserved_mem = mem_max * const.CSM_USAGE_RESERVED_BUFFER_PERCENT // 100
        quota = (mem_max - reserved_mem) // const.MAX_MEM_PER_REQUEST_MB
        return quota

    @staticmethod
    def _mem_limit_to_int(mem: str) -> int:
        """
        Convert memory limit from Conf to integer, e.g. '128Mi' -> 128.

        :param mem: value from Conf as string.
        :returns: integer value.
        """
        numbers_only = mem[:mem.find('M')]
        return int(numbers_only)

    @staticmethod
    def _cpu_limit_to_int(cpu: str) -> int:
        """
        Convert CPU limit from Conf string to integer, e.g. '250m' -> 250.

        :param cpu: value from Conf as string.
        :returns: integer value.
        """
        numbers_only = cpu[:cpu.find('m')]
        return int(numbers_only)

    @staticmethod
    def set_resource_limits() -> None:
        """Set resource limits for CSM."""
        Log.info("Config: Fetching CSM services cpu and memory limits")
        count_services : str = Conf.get(const.CONSUMER_INDEX,
            const.CSM_LIMITS_NUM_SERVICES_KEY)
        try:
            count_services = int(count_services)
        except ValueError:
            raise CsmSetupError("CSM num_services value is not a valid"
                " integer.")
        for count in range(count_services):
            name = Conf.get(const.CONSUMER_INDEX,
                f'{const.CSM_LIMITS_SERVICES_KEY}[{count}]>name')
            if name == "agent":
                mem_min = Conf.get(const.CONSUMER_INDEX,
                    f'{const.CSM_LIMITS_SERVICES_KEY}[{count}]>memory>min')
                mem_max = Conf.get(const.CONSUMER_INDEX,
                    f'{const.CSM_LIMITS_SERVICES_KEY}[{count}]>memory>max')
                cpu_min = Conf.get(const.CONSUMER_INDEX,
                    f'{const.CSM_LIMITS_SERVICES_KEY}[{count}]>cpu>min')
                cpu_max = Conf.get(const.CONSUMER_INDEX,
                    f'{const.CSM_LIMITS_SERVICES_KEY}[{count}]>cpu>max')

                mem_min = Configure._mem_limit_to_int(mem_min)
                mem_max = Configure._mem_limit_to_int(mem_max)
                cpu_min = Configure._cpu_limit_to_int(cpu_min)
                cpu_max = Configure._cpu_limit_to_int(cpu_max)

                request_quota = Configure._calculate_request_quota(
                    mem_min, mem_max, cpu_min, cpu_max)
                Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_REQUEST_QUOTA,
                    request_quota)
            else:
                raise CsmSetupError("CSM agent service mem and cpu limits are"
                    " not found")
