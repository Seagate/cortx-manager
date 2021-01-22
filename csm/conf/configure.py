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
from ipaddress import ip_address
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kvstore.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.conf.uds import UDSConfigGenerator
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL

class Configure(Setup):
    """
    Perform configuration for csm
        : Move conf file to etc
    Config is used to move update conf files one time configuration
    """
    def __init__(self):
        super(Configure, self).__init__()
        Log.info("Triggering csm_setup config")
        self._debug_flag = None
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
            Conf.load(const.DATABASE_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CORTXCLI_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        if command.options.get(const.DEBUG) == 'true' or Conf.get(const.CONSUMER_INDEX,
                f"{const.CLUSTER}>{const.DEPLOYMENT}>{const.MODE}") == "DEV":
            Log.info("Running Csm Setup for Development Mode.")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
            self._debug_flag = True
        try:
            if not self._debug_flag:
                uds_public_ip = command.options.get('uds_public_ip')
                if uds_public_ip is not None:
                    ip_address(uds_public_ip)
                UDSConfigGenerator.apply(uds_public_ip=uds_public_ip)
                Configure._set_node_id()
                minion_id = Configure._get_minion_id()
                data_nw = Configure._get_data_nw_info(minion_id)
                Configure._set_db_host_addr('consul',
                                            data_nw.get('roaming_ip', 'localhost'))
                Configure._set_db_host_addr('es', data_nw.get('pvt_ip_addr', 'localhost'))
                Configure._set_fqdn_for_nodeid()
                Configure._set_healthmap_path()
                Configure._set_rmq_cluster_nodes()
            self._rsyslog()
            self._logrotate()
            self._rsyslog_common()
            if not self._replacement_node_flag:
                self.create()
        except Exception as e:
            import traceback
            Log.error(f"csm_setup config command failed. Error: {e} - {str(traceback.format_exc())}")
            raise CsmSetupError(f"csm_setup config command failed. Error: {e} - {str(traceback.format_exc())}")
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """
        Log.error("Creating CSM Conf File on Required Location.")
        if not self._debug_flag:
            Configure.store_encrypted_password()
        Conf.save(const.CSM_GLOBAL_INDEX)
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")

    @staticmethod
    def store_encrypted_password():
        """
        :return:
        """
        # read username's and password's for S3 and RMQ
        Log.info("Storing Encrypted Password")
        open_ldap_user = Conf.get(const.CONSUMER_INDEX,
                                  f"{const.OPENLDAP}>sgiam>user")
        open_ldap_secret = Conf.get(const.CONSUMER_INDEX,
                                    f"{const.OPENLDAP}>sgiam>secret")
        # Edit Current Config File.
        if open_ldap_user and open_ldap_secret:
            Log.info("Open-Ldap Credentials Copied to CSM Configuration.")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_LOGIN}",
                     open_ldap_user)
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_PASSWORD}",
                     open_ldap_secret)
        # TODO:  Change Keys Here.
        sspl_config = Conf.get(const.CONSUMER_INDEX, const.SSPL)
        if sspl_config and isinstance(sspl_config, dict):
            Log.info("SSPL Credentials Copied to CSM Configuration.")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.USERNAME}",
                     sspl_config.get(const.USERNAME))
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.PASSWORD}",
                     sspl_config.get(const.PASSWORD))
        _paswd = Setup._fetch_csm_user_password()
        if not _paswd:
            raise CsmSetupError("CSM Password Not Found.")
        cluster_id = Conf.get(const.CONSUMER_INDEX,
                              f"{const.CLUSTER}>{const.CLUSTER_ID}")
        Log.info("Cluster Id Copied to CSM Configuration.")
        Conf.set(const.CSM_GLOBAL_INDEX,
                 f"{const.PROVISIONER}>{const.CLUSTER_ID}", cluster_id)
        Log.info("CSM Credentials Copied to CSM Configuration.")
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CSM}>{const.PASSWORD}", _paswd)

    def cli_create(self, command):
        """
        This Function Creates the CortxCli Conf File on Required Location.
        :return:
        """
        os.makedirs(const.CORTXCLI_PATH, exist_ok=True)
        os.makedirs(const.CORTXCLI_CONF_PATH, exist_ok=True)
        Setup._run_cmd(
            f"setfacl -R -m u:{const.NON_ROOT_USER}:rwx {const.CORTXCLI_PATH}")
        Setup._run_cmd(
            f"setfacl -R -m u:{const.NON_ROOT_USER}:rwx {const.CORTXCLI_CONF_PATH}")
        Conf.set(const.CORTXCLI_GLOBAL_INDEX,
                 f"{const.CORTXCLI_SECTION}>{const.CSM_AGENT_HOST_PARAM_NAME}" ,
                 command.options.get(const.ADDRESS_PARAM, "127.0.0.1"))
        if self._debug_flag:
            Conf.set(const.CORTXCLI_GLOBAL_INDEX,
                     f"{const.DEPLOYMENT}>{const.MODE}", const.DEV)
        Setup._run_cmd(
            f"cp -rn {const.CORTXCLI_SOURCE_CONF_PATH} {const.ETC_PATH}")

    @staticmethod
    def _set_node_id():
        """
        This method gets the nodes id from provisioner cli and updates
        in the config.
        """
        # Get get node id and set to config
        node_id_data = Conf.get(const.CONSUMER_INDEX, const.GET_NODE_ID)
        if node_id_data:
            Log.info(f"Node ids obtained from Conf Store:{node_id_data}")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.NODE1}",
                     f"{const.NODE}{node_id_data[const.MINION_NODE1_ID]}")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.NODE2}",
                     f"{const.NODE}{node_id_data[const.MINION_NODE2_ID]}")
        else:
            Log.error("Unable to fetch system node ids info.")
            raise CsmSetupError("Unable to fetch system node ids info.")

    @staticmethod
    def _get_minion_id():
        """
        Obtains current minion id. If it cannot be obtained, returns default node #1 id.
        """
        Log.info("Fetching Minion Id.")
        minion_id = Conf.get(const.CONSUMER_INDEX, const.ID)
        if not minion_id:
            raise CsmSetupError('Unable to obtain current minion id')
        return minion_id

    @staticmethod
    def _get_data_nw_info(minion_id):
        """
        Obtains minion data network info.

        :param minion_id: Minion id.
        """
        Log.info("Fetching data N/W info.")
        data_nw = Conf.get(const.CONSUMER_INDEX, f'cluster>{minion_id}>network>data_nw')
        if not data_nw:
            raise CsmSetupError(
                f'Unable to obtain data nw info for {minion_id}')
        return data_nw

    @staticmethod
    def _set_db_host_addr(backend, addr):
        """
        Sets database backend host address in CSM config.

        :param backend: Databased backend. Supports Elasticsearch('es'), Consul ('consul').
        :param addr: Host address.
        """
        if backend not in ('es', 'consul'):
            raise CsmSetupError(f'Invalid database backend "{addr}"')
        key = f'databases.{backend}_db.config.host'
        try:
            Conf.set(const.DATABASE_INDEX, key, addr)
        except Exception as e:
            raise CsmSetupError(f'Unable to set {backend} host address: {e}')

    def _rsyslog(self):
        """
        Configure rsyslog
        """
        Log.info("Configuring rsyslog")
        if os.path.exists(const.RSYSLOG_DIR):
            Setup._run_cmd(f"cp -f {const.SOURCE_RSYSLOG_PATH} {const.RSYSLOG_PATH}")
            Setup._run_cmd("systemctl restart rsyslog")
        else:
            Log.error(f"rsyslog failed. {const.RSYSLOG_DIR} directory missing.")
            raise CsmSetupError(f"rsyslog failed. {const.RSYSLOG_DIR} directory missing.")

    def _rsyslog_common(self):
        """
        Configure common rsyslog and logrotate
        Also cleanup statsd
        """
        if os.path.exists(const.CRON_DIR):
            Setup._run_cmd(f"cp -f {const.SOURCE_CRON_PATH} {const.DEST_CRON_PATH}")
            setup_info = Conf.get(const.CONSUMER_INDEX, const.GET_SETUP_INFO)
            if self._debug_flag or (setup_info and setup_info[const.STORAGE_TYPE] == const.STORAGE_TYPE_VIRTUAL):
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
            setup_info = Conf.get(const.CONSUMER_INDEX, const.GET_SETUP_INFO)
            if self._debug_flag or (setup_info and setup_info[
                const.STORAGE_TYPE] == const.STORAGE_TYPE_VIRTUAL):
                sed_script = f's/\\(.*rotate\\s\\+\\)[0-9]\\+/\\1{const.LOGROTATE_AMOUNT_VIRTUAL}/'
                sed_cmd = f"sed -i -e {sed_script} {const.CSM_LOGROTATE_DEST}"
                Setup._run_cmd(sed_cmd)
            Setup._run_cmd(f"chmod 644 {const.CSM_LOGROTATE_DEST}")
        else:
            Log.error(f"logrotate failed. {const.LOGROTATE_DIR_DEST} dir missing.")
            raise CsmSetupError(f"logrotate failed. {const.LOGROTATE_DIR_DEST} dir missing.")

    @staticmethod
    def _set_fqdn_for_nodeid():
        # TODO: Change Below Keys.
        nodes = Conf.get(const.CONSUMER_INDEX, const.NODE_LIST_KEY)
        Log.debug("Node ids obtained from salt-call:{nodes}")
        if nodes:
            for each_node in nodes:
                # TODO: Change Below Keys.
                hostname = Conf.get(
                    const.PILLAR_GET, f"{const.CLUSTER}:{each_node}:{const.HOSTNAME}")
                Log.debug(f"Setting hostname for {each_node}:{hostname}. Default: {each_node}")
                if hostname:
                    Conf.set(const.CSM_GLOBAL_INDEX,
                             f"{const.MAINTENANCE}.{each_node}", f"{hostname}")
                else:
                    Conf.set(const.CSM_GLOBAL_INDEX,
                             f"{const.MAINTENANCE}.{each_node}", f"{each_node}")

    @staticmethod
    def _set_healthmap_path():
        """
        This method gets the healthmap path fron salt command and saves the
        value in csm.conf config.
        Fetching the minion id of the node where this cli command is fired.
        This minion id will be required to fetch the healthmap path.
        Will use 'srvnode-1' in case the salt command fails to fetch the id.
        """
        minion_id = None
        healthmap_folder_path = None
        healthmap_filename = None
        # TODO: Change Below Keys.
        minion_id = Conf.get(const.CONSUMER_INDEX, const.ID)
        if not minion_id:
            Log.logger.warn((f"Unable to fetch minion id for the node."
                             f"Using {const.MINION_NODE1_ID}."))
            minion_id = const.MINION_NODE1_ID
        try:
            # TODO: Change Below Keys.
            healthmap_folder_path = Conf.get(
                const.CONSUMER_INDEX, 'sspl:health_map_path')
            if not healthmap_folder_path:
                Log.logger.error("Fetching health map folder path failed.")
                raise CsmSetupError("Fetching health map folder path failed.")
            # TODO: Change Below Keys.
            healthmap_filename = Conf.get(
                const.CONSUMER_INDEX, 'sspl:health_map_file')
            if not healthmap_filename:
                Log.logger.error("Fetching health map filename failed.")
                raise CsmSetupError("Fetching health map filename failed.")
            healthmap_path = os.path.join(healthmap_folder_path, healthmap_filename)
            if not os.path.exists(healthmap_path):
                Log.logger.error("Health map not available at {healthmap_path}")
                raise CsmSetupError("Health map not available at {healthmap_path}")
            """
            Setting the health map path to csm.conf configuration file.
            """
            Conf.set(const.CSM_GLOBAL_INDEX, const.HEALTH_SCHEMA_KEY, healthmap_path)
        except Exception as e:
            raise CsmSetupError(f"Setting Health map path failed. {e}")

    @staticmethod
    def _set_rmq_cluster_nodes():
        """
        Obtains minion names and use them to configure RabbitMQ nodes on the config file.
        """
        try:
            # TODO: Change the Keys Below.
            minions = Conf.get(const.CONSUMER_INDEX, const.ID)
            minions.sort()
            conf_key = f"{const.CHANNEL}>{const.RMQ_HOSTS}"
            Conf.set(const.CSM_GLOBAL_INDEX, conf_key, minions)
        except KvError as e:
            raise CsmSetupError(f"Setting RMQ cluster nodes failed {e}.")
