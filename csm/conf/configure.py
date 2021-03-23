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
from cortx.utils.product_features import unsupported_features
from csm.common.payload import Json
from ipaddress import ip_address
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.validator.v_network import NetworkV
from cortx.utils.validator.v_consul import ConsulV
from cortx.utils.validator.v_elasticsearch import ElasticsearchV


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
        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DB_SOURCE_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        self._prepare_and_validate_confstore_keys()
        self._validate_consul_service()
        self._validate_es_service()
        self._set_deployment_mode()
        try:
            self._configure_uds_keys()
            if not self._is_env_vm:
                Configure._validate_healthmap_path()
            self._rsyslog()
            self._logrotate()
            self._rsyslog_common()
            await self._set_unsupported_feature_info()
            if not self._replacement_node_flag:
                self.create()
        except Exception as e:
            import traceback
            err_msg = (f"csm_setup config command failed. Error: "
                       f"{e} - {str(traceback.format_exc())}")
            Log.error(err_msg)
            raise CsmSetupError(err_msg)
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SERVER_NODE_INFO:f"{const.SERVER_NODE_INFO}",
            const.KEY_SERVER_NODE_TYPE:f"{const.SERVER_NODE_INFO}>{const.TYPE}",
            const.KEY_ENCLOSURE_ID:f"{const.SERVER_NODE_INFO}>{const.STORAGE}>{const.ENCLOSURE_ID}",
            const.KEY_DATA_NW_PUBLIC_FQDN:f"{const.SERVER_NODE_INFO}>{const.NETWORK}>{const.DATA}>{const.PUBLIC_FQDN}",
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}",
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}"
            })

        self._validate_conf_store_keys(const.CONSUMER_INDEX)

    def _validate_consul_service(self):
        Log.info("Getting consul status")
        # get host and port of consul database from conf
        host = Conf.get(const.DATABASE_INDEX, 'databases>consul_db>config>host')
        if not host: raise CsmSetupError("Consul host not available.")
        port = Conf.get(const.DATABASE_INDEX, 'databases>consul_db>config>port')
        if not port: raise CsmSetupError("Consul port not available.")
        # Validation throws exception on failure
        ConsulV().validate('service', [host, port])

    def _validate_es_service(self):
        Log.info("Getting elasticsearch status")
        # get host and port of consul database from conf
        host = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>host')
        if not host: raise CsmSetupError("Elasticsearch host not available.")
        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        if not port: raise CsmSetupError("Elasticsearch port not available.")
        # Validation throws exception on failure
        ElasticsearchV().validate('service', [host, port])

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
        os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")

    def _rsyslog(self):
        """
        Configure rsyslog
        """
        Log.info("Configuring rsyslog")
        os.makedirs(const.RSYSLOG_DIR, exist_ok=True)
        if os.path.exists(const.RSYSLOG_DIR):
            Setup._run_cmd(f"cp -f {const.SOURCE_RSYSLOG_PATH} {const.RSYSLOG_PATH}")
            Setup._run_cmd("systemctl restart rsyslog")
        else:
            msg = f"rsyslog failed. {const.RSYSLOG_DIR} directory missing."
            Log.error(msg)
            raise CsmSetupError(msg)

    def _rsyslog_common(self):
        """
        Configure common rsyslog and logrotate
        Also cleanup statsd
        """
        if os.path.exists(const.CRON_DIR):
            Setup._run_cmd(f"cp -f {const.SOURCE_CRON_PATH} {const.DEST_CRON_PATH}")
            if self._setup_info and self._setup_info[
                const.STORAGE_TYPE] == const.STORAGE_TYPE_VIRTUAL:
                sed_script = f'\
                    s/\\(.*es_cleanup.*-d\\s\\+\\)[0-9]\\+/\\1{const.ES_CLEANUP_PERIOD_VIRTUAL}/'
                sed_cmd = f"sed -i -e {sed_script} {const.DEST_CRON_PATH}"
                Setup._run_cmd(sed_cmd)
        else:
            raise CsmSetupError(f"cron failed. {const.CRON_DIR} dir missing.")

    def _logrotate(self):
        """
        Configure logrotate
        """
        Log.info("Configuring logrotate.")
        source_logrotate_conf = const.SOURCE_LOGROTATE_PATH
        if not os.path.exists(const.LOGROTATE_DIR_DEST):
            Setup._run_cmd(f"mkdir -p {const.LOGROTATE_DIR_DEST}")
        if os.path.exists(const.LOGROTATE_DIR_DEST):
            Setup._run_cmd(f"cp -f {source_logrotate_conf} {const.CSM_LOGROTATE_DEST}")
            if (self._setup_info and self._setup_info[
                const.STORAGE_TYPE] == const.STORAGE_TYPE_VIRTUAL):
                sed_script = f's/\\(.*rotate\\s\\+\\)[0-9]\\+/\\1{const.LOGROTATE_AMOUNT_VIRTUAL}/'
                sed_cmd = f"sed -i -e {sed_script} {const.CSM_LOGROTATE_DEST}"
                Setup._run_cmd(sed_cmd)
            Setup._run_cmd(f"chmod 644 {const.CSM_LOGROTATE_DEST}")
        else:
            err_msg = f"logrotate failed. {const.LOGROTATE_DIR_DEST} dir missing."
            Log.error(err_msg)
            raise CsmSetupError(err_msg)

    @staticmethod
    def _validate_healthmap_path():
        """
        This method gets the healthmap path fron salt command and saves the
        value in csm.conf config.
        Fetching the minion id of the node where this cli command is fired.
        This minion id will be required to fetch the healthmap path.
        Will use 'srvnode-1' in case the salt command fails to fetch the id.
        """
        Log.info("Validating Healthmap path")
        healthmap_path = Conf.get(const.CSM_GLOBAL_INDEX, const.HEALTH_SCHEMA_KEY)
        if not os.path.exists(healthmap_path):
            Log.logger.error(f"Health map not available at {healthmap_path}")
            raise CsmSetupError(f"Health map not available at {healthmap_path}")

    def _configure_uds_keys(self):
        Log.info("Configuring UDS keys")
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        virtual_host_key = f"{const.CLUSTER}>{cluster_id}>{const.NETWORK}>{const.MANAGEMENT}>{const.VIRTUAL_HOST}"
        self._validate_conf_store_keys(const.CONSUMER_INDEX,[virtual_host_key])
        virtual_host = Conf.get(const.CONSUMER_INDEX, virtual_host_key)
        data_nw_public_fqdn = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_DATA_NW_PUBLIC_FQDN] )
        Log.debug(f"Validating connectivity for virtual_host:{virtual_host}, data_nw_public_fqdn:{data_nw_public_fqdn}")
        try:
            NetworkV().validate('connectivity', [virtual_host, data_nw_public_fqdn])
        except Exception as e:
            raise CsmSetupError("Network Validation failed.")
        Log.info(f"Set virtual_host:{virtual_host}, data_nw_public_fqdn:{data_nw_public_fqdn} to csm config")
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.PROVISIONER}>{const.VIRTUAL_HOST}", virtual_host)
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.PROVISIONER}>{const.PUBLIC_DATA_DOMAIN_NAME}", data_nw_public_fqdn)

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
