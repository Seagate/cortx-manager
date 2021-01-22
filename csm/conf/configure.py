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
from csm.common.process import SimpleProcess

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
            Conf.load(const.DATABASE_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CORTXCLI_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        self._set_deployment_mode()
        try:
            if not self._is_env_vm:
                uds_public_ip = command.options.get('uds_public_ip')
                if uds_public_ip is not None:
                    ip_address(uds_public_ip)
                UDSConfigGenerator.apply(uds_public_ip=uds_public_ip)
                Configure._set_node_id()
                machine_id = Configure._get_machine_id()
                data_nw = Configure._get_data_nw_info(machine_id)
                Configure._set_db_host_addr('consul',
                                        data_nw.get('public_ip', 'localhost'))
                Configure._set_db_host_addr('es',
                                        data_nw.get('private_ip', 'localhost'))
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
        if not self._is_env_vm:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.VM)
        self.store_encrypted_password()
        Conf.save(const.CSM_GLOBAL_INDEX)
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")

    def store_encrypted_password(self):
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
        sspl_config = Conf.get(const.CONSUMER_INDEX,
                               "rabbitmq>sspl>RABBITMQEGRESSPROCESSOR")
        if sspl_config and isinstance(sspl_config, dict):
            Log.info("SSPL Credentials Copied to CSM Configuration.")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.USERNAME}",
                     sspl_config.get(const.USERNAME))
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.PASSWORD}",
                     sspl_config.get(const.PASSWORD))
        _paswd = self._fetch_csm_user_password()
        if not _paswd:
            raise CsmSetupError("CSM Password Not Found.")
        cluster_id = Conf.get(const.CONSUMER_INDEX,
                              f"{const.CLUSTER}>{const.CLUSTER_ID}")
        Log.info("Cluster Id Copied to CSM Configuration.")
        Conf.set(const.CSM_GLOBAL_INDEX,
                 f"{const.PROVISIONER}>{const.CLUSTER_ID}", cluster_id)
        Log.info("CSM Credentials Copied to CSM Configuration.")
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CSM}>{const.PASSWORD}",
                 _paswd)
        service_user = Conf.get(const.CONSUMER_INDEX, f"service>cortx>user")
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CSM}>{const.USERNAME}",
                 service_user)

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
        if self._is_env_vm:
            Conf.set(const.CORTXCLI_GLOBAL_INDEX,
                     f"{const.DEPLOYMENT}>{const.MODE}", const.VM)
        Setup._run_cmd(
            f"cp -rn {const.CORTXCLI_SOURCE_CONF_PATH} {const.ETC_PATH}")

    @staticmethod
    def _set_node_id():
        """
        This method gets the nodes id from provisioner cli and updates
        in the config.
        """

        server_nodes = Conf.get(const.CONSUMER_INDEX, "cluster>server_nodes")
        for each_node in server_nodes.values():
            node_id = Conf.get(const.CONSUMER_INDEX,
                               f"cluster>{each_node}>node_id")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}>{const.NODE1}",
                     f"{const.NODE}{node_id}")
        else:
            Log.error("Unable to fetch system node ids info.")
            raise CsmSetupError("Unable to fetch system node ids info.")

    @staticmethod
    def _get_machine_id():
        """
        Obtains current minion id. If it cannot be obtained, returns default node #1 id.
        """
        Log.info("Fetching Machine Id.")
        cmd = "cat /etc/machine-id"
        proc_obj = SimpleProcess(cmd)
        machine_id, _err, _returncode = proc_obj.run()
        if _returncode != 0:
            raise CsmSetupError('Unable to obtain current machine id.')
        return machine_id

    @staticmethod
    def _get_data_nw_info(machine_id):
        """
        Obtains minion data network info.

        :param machine_id: Minion id.
        """
        Log.info("Fetching data N/W info.")
        data_nw = Conf.get(const.CONSUMER_INDEX,
                           f'cluster>{machine_id}>network>data')
        if not data_nw:
            raise CsmSetupError(
                f'Unable to obtain data nw info for {machine_id}')
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
            setup_info = Conf.get(const.CONSUMER_INDEX, const.GET_SETUP_INFO)
            if self._is_env_vm or (setup_info and setup_info[const.STORAGE_TYPE] == const.STORAGE_TYPE_VIRTUAL):
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
            if self._is_env_vm or (setup_info and setup_info[
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
    def _set_fqdn_for_nodeid():
        nodes = Conf.get(const.CONSUMER_INDEX, "cluster>server_nodes")
        Log.debug("Node Name and Machine ID Fetched from Consumer.")
        if nodes:
            for each_node in nodes.values():
                hostname = Conf.get(const.CONSUMER_INDEX,
                    f"{const.CLUSTER}>{each_node}>{const.HOSTNAME}")
                Log.debug((f"Setting hostname for {each_node}:{hostname}."
                           f" Default: {each_node}"))
                Conf.set(const.CSM_GLOBAL_INDEX,
                         f"{const.MAINTENANCE}>{each_node}",
                         f"{hostname}" or f"{each_node}")

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
        machine_id = Configure._get_machine_id()
        try:
            # TODO: Change Below Keys.
            healthmap_folder_path = Conf.get(
                const.CONSUMER_INDEX, 'sspl>health_map_path')
            if not healthmap_folder_path:
                Log.logger.error("Fetching health map folder path failed.")
                raise CsmSetupError("Fetching health map folder path failed.")
            # TODO: Change Below Keys.
            healthmap_filename = Conf.get(
                const.CONSUMER_INDEX, 'sspl>health_map_file')
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
            server_nodes = Conf.get(const.CONSUMER_INDEX, "cluster>server_nodes")
            node_id_list = list(server_nodes.values())
            conf_key = f"{const.CHANNEL}>{const.RMQ_HOSTS}"
            Conf.set(const.CSM_GLOBAL_INDEX, conf_key, node_id_list.sort())
        except KvError as e:
            raise CsmSetupError(f"Setting RMQ cluster nodes failed {e}.")
