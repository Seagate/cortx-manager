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
import crypt
import socket
from cortx.utils.log import Log
from ipaddress import ip_address
from csm.conf.setup import Setup, CsmSetupError
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.validator.v_network import NetworkV
from cortx.utils.validator.error import VError


class Prepare(Setup):
    """
    Reset csm Configuration.
    """
    def __init__(self):
        super(Prepare, self).__init__()
        Log.info("Triggering csm_setup prepare")
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
            self.load_csm_config_indices()
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")


        services = command.options.get("services")
        if ',' in services:
            services = services.split(",")
        elif 'all' in services:
            services = ["agent", "web", "cli"]
        else:
            services=[services]
        self.execute_web_and_cli(command.options.get("config_url"),
                                    services,
                                    command.sub_command_name)
        if not "agent" in services:
            return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

        self._prepare_and_validate_confstore_keys()
        self._set_secret_string_for_decryption()
        self._set_cluster_id()
        self._set_ldap_servers()
        # TODO: set configurations of perf stats once keys are available in conf-store.
        # self._set_msgbus_perf_stat_info()
        self._set_db_host_addr()
        self._set_csm_ldap_credentials()
        self._set_ldap_params()
        self.create()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
                const.KEY_SERVER_NODE_INFO:f"{const.NODE}>{self.machine_id}",
                const.KEY_SERVER_NODE_TYPE:f"{const.ENV_TYPE_KEY}",
                const.KEY_HOSTNAME:f"{const.NODE}>{self.machine_id}>{const.HOSTNAME}",
                const.KEY_CLUSTER_ID:f"{const.NODE}>{self.machine_id}>{const.CLUSTER_ID}",
                # TODO: confirm following keys: add csm user and secret using L123
                const.KEY_CSM_LDAP_USER:f"{const.CSM_AGENT_AUTH_ADMIN_KEY}",
                const.KEY_CSM_LDAP_SECRET:f"{const.CSM_AGENT_AUTH_SECRET_KEY}",
                const.CONSUL_ENDPOINTS_KEY:f"{const.CONSUL_ENDPOINTS_KEY}",
                const.CONSUL_SECRET_KEY:f"{const.CONSUL_SECRET_KEY}",
                const.OPENLDAP_ENDPOINTS:f"{const.OPENLDAP_ENDPOINTS_KEY}",
                const.OPENLDAP_SERVERS:f"{const.OPENLDAP_SERVERS_KEY}",
                const.OPENLDAP_ROOT_ADMIN:f"{const.OPENLDAP_ROOT_ADMIN_KEY}",
                const.OPENLDAP_ROOT_SECRET:f"{const.OPENLDAP_ROOT_SECRET_KEY}",
                const.OPENLDAP_BASEDN:f"{const.OPENLDAP_BASEDN_KEY}",
                # TODO: validate following keys once available in conf-store
                #const.METRICS_PERF_STATS_MSG_TYPE : const.METRICS_PERF_STATS_MSG_TYPE_KEY,
                #const.METRICS_PERF_STATS_RETENTION_SIZE:const.METRICS_PERF_STATS_RETENTION_SIZE_KEY
                })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def _set_secret_string_for_decryption(self):
        '''
        This will be the root of csm secret key
        eg: for "cortx>software>csm>secret" root is "cortx"
        '''
        Log.info("Set decryption keys for CSM and S3")

        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_PASSWORD_DECRYPTION_KEY,
                    self.conf_store_keys[const.KEY_CSM_LDAP_SECRET].split('>')[0])

    def _set_cluster_id(self):
        Log.info("Setting up cluster id")
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        if not cluster_id:
            raise CsmSetupError("Failed to fetch cluster id")
        Conf.set(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY, cluster_id)


    def _get_ldap_hosts_info(self):
        """
        Obtains list of ldap host address
        :return: list of ip where ldap is running
        """
        Log.info("Fetching ldap hosts info.")
        ldap_endpoints = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.OPENLDAP_ENDPOINTS])
        if ldap_endpoints:
            Log.info(f"Fetching ldap endpoint.{ldap_endpoints}")
            protocol, host, port = self._parse_endpoints(ldap_endpoints)
            # resolved_ip = socket.gethostbyname(host)
            return [host], port
        else:
            raise CsmSetupError("LDAP endpoints not found.")

    def _set_ldap_servers(self):
        ldap_servers = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.OPENLDAP_SERVERS])
        ldap_servers_count = len(ldap_servers)
        Conf.set(const.DATABASE_INDEX, const.OPEN_LDAP_SERVERS_COUNT, str(ldap_servers_count))
        for each_server_count in range(ldap_servers_count):
            Conf.set(const.DATABASE_INDEX,
                    f'{const.OPEN_LDAP_SERVERS}[{each_server_count}]',
                    eval(f'{ldap_servers}[{each_server_count}]'))

    def _set_db_host_addr(self):
        """
        Sets database hosts address in CSM config.
        :return:
        """
        ldap_hosts, ldap_port = self._get_ldap_hosts_info()
        protocols, consul_host, consul_port, secret, endpoints = self._get_consul_config()
        consul_login = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ADMIN_KEY)
        try:
            consul_servers_count = len([consul_host])
            Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_HOST_COUNT, str(consul_servers_count))
            for each_consul_host in range(consul_servers_count):
                Conf.set(const.DATABASE_INDEX,
                        f'{const.DB_CONSUL_CONFIG_HOST}[{each_consul_host}]',
                        eval(f'{consul_host}[{each_consul_host}]'))
            if consul_port:
                Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_PORT, consul_port)
            Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_PASSWORD, secret)
            Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_LOGIN, consul_login)
            ldap_hosts_count = len(ldap_hosts)
            Conf.set(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_HOSTS_COUNT, str(ldap_hosts_count))
            for each_ldap_host in range(ldap_hosts_count):
                Conf.set(const.DATABASE_INDEX,
                        f'{const.DB_OPENLDAP_CONFIG_HOSTS}[{each_ldap_host}]',
                        eval(f'{ldap_hosts}[{each_ldap_host}]'))
            Conf.set(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_PORT, ldap_port)
        except Exception as e:
            Log.error(f'Unable to set host address: {e}')
            raise CsmSetupError(f'Unable to set host address: {e}')

    def _set_csm_ldap_credentials(self):
        # read username's and password's for S3 and RMQ
        Log.info("Storing S3 credentials")
        base_dn = Conf.get(const.CONSUMER_INDEX,
                                    self.conf_store_keys[const.OPENLDAP_BASEDN],
                                    const.DEFAULT_BASE_DN)
        csm_ldap_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CSM_LDAP_USER])
        csm_ldap_secret = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CSM_LDAP_SECRET])
        # Edit Current Config File.
        if csm_ldap_user and csm_ldap_secret:
            Log.info("Open-Ldap Credentials Copied to CSM Configuration.")
            Conf.set(const.CSM_GLOBAL_INDEX, const.LDAP_AUTH_CSM_USER, csm_ldap_user)
            Conf.set(const.CSM_GLOBAL_INDEX, const.LDAP_AUTH_CSM_SECRET, csm_ldap_secret)
            Conf.set(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_LOGIN, f"cn={csm_ldap_user},{base_dn}")
            Conf.set(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_PASSWORD, csm_ldap_secret)


    def store_encrypted_password(self):
        """
        :return:
        """
        _paswd = self._fetch_csm_user_password()
        if not _paswd:
            raise CsmSetupError("CSM Password Not Found.")

        Log.info("CSM Credentials Copied to CSM Configuration.")
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CSM}>{const.PASSWORD}",
                 _paswd)
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.PROVISIONER}>{const.PASSWORD}",
                 _paswd)
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CSM}>{const.USERNAME}",
                 self._user)
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.PROVISIONER}>{const.USERNAME}",
                 self._user)

    def _set_ldap_params(self):
        """
        Sets openldap configuration in CSM config.
        :return:
        """
        base_dn = Conf.get(const.CONSUMER_INDEX,
                                    self.conf_store_keys[const.OPENLDAP_BASEDN],
                                    const.DEFAULT_BASE_DN)
        ldap_root_admin_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.OPENLDAP_ROOT_ADMIN], 'admin')
        ldap_root_secret = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.OPENLDAP_ROOT_SECRET])
        bind_base_dn = f"cn={ldap_root_admin_user},{base_dn}"
        Log.info(f"Set base_dn:{base_dn} and bind_base_dn:{bind_base_dn} for openldap")
        Conf.set(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_BASE_DN,base_dn)
        Conf.set(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_BIND_BASE_DN, bind_base_dn)
        Conf.set(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_ADMIN_USER, ldap_root_admin_user)
        Conf.set(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_ADMIN_SECRET, ldap_root_secret)

    def _set_msgbus_perf_stat_info(self):
        msg_type = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.METRICS_PERF_STATS_MSG_TYPE])
        retention_size = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.METRICS_PERF_STATS_RETENTION_SIZE])
        Log.info(f"Set message_type:{msg_type} and retention_size:{retention_size} for perf_stat")
        Conf.set(const.CSM_GLOBAL_INDEX, const.MSG_BUS_PERF_STAT_MSG_TYPE, msg_type)
        Conf.set(const.CSM_GLOBAL_INDEX, const.MSG_BUS_PERF_STAT_RETENTION_SIZE, retention_size)

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, const.CSM_DEPLOYMENT_MODE,
                     const.DEV)
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)
