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


from cortx.utils.log import Log
from cortx.utils.validator.v_network import NetworkV
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL


class Prepare(Setup):
    """
    Prepare CORTX CLI

    Post install is used after just all rpms are install but
    no service are started
    """

    def __init__(self):
        super(Prepare, self).__init__()
        Setup._copy_cli_skeleton_configs()

    async def execute(self, command):
        """
        Execute CORTX CLI setup Prepare Command

        :param command: Command Object For CLI. :type: Command
        :return: 0 on success, RC != 0 otherwise.
        """

        Log.info("Executing Prepare for CORTX CLI")
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CLI_CONF_URL)
            Conf.load(const.DATABASE_CLI_INDEX, const.DATABASE_CLI_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")

        self._prepare_and_validate_confstore_keys()
        self._set_deployment_mode()
        self._set_fqdn_for_nodeid()
        self._set_cluster_id()
        self._set_secret_string_for_decryption()
        self._set_s3_ldap_credentials()
        self._set_db_host_addr()
        self._set_csm_credentials()
        self.create()

        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SERVER_NODE_INFO:f"{const.SERVER_NODE_INFO}",
            const.KEY_SERVER_NODE_TYPE:f"{const.SERVER_NODE_INFO}>{const.TYPE}",
            const.KEY_ENCLOSURE_ID:f"{const.SERVER_NODE_INFO}>{const.STORAGE}>{const.ENCLOSURE_ID}",
            const.KEY_DATA_NW_PRIVATE_FQDN:f"{const.SERVER_NODE_INFO}>{const.NETWORK}>{const.DATA}>{const.PRIVATE_FQDN}",
            const.KEY_HOSTNAME:f"{const.SERVER_NODE_INFO}>{const.HOSTNAME}",
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}",
            const.KEY_S3_LDAP_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.OPENLDAP}>{const.SGIAM}>{const.USER}",
            const.KEY_S3_LDAP_SECRET:f"{const.CORTX}>{const.SOFTWARE}>{const.OPENLDAP}>{const.SGIAM}>{const.SECRET}",
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}",
            const.KEY_CSM_SECRET:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.SECRET}",})
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
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.CSM}>password_decryption_key",
                    self.conf_store_keys[const.KEY_CSM_SECRET].split('>')[0])
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.S3}>password_decryption_key",
                    self.conf_store_keys[const.KEY_S3_LDAP_SECRET].split('>')[0])

    def _set_fqdn_for_nodeid(self):
        Log.info("Setting hostname to server node name")
        server_node_info = Conf.get(const.CONSUMER_INDEX, const.SERVER_NODE)
        Log.debug(f"Server node information: {server_node_info}")
        for machine_id, node_data in server_node_info.items():
            hostname = node_data.get(const.HOSTNAME, const.NAME)
            node_name = node_data.get(const.NAME)
            Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.MAINTENANCE}>{node_name}",f"{hostname}")

    def _set_cluster_id(self):
        Log.info("Setting up cluster id")
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        if not cluster_id:
            raise CsmSetupError("Failed to fetch cluster id")
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, const.CLUSTER_ID_KEY, cluster_id)

    def _get_es_hosts_info(self):
        """
        Obtains list of elasticsearch hosts ip running in a cluster
        :return: list of elasticsearch hosts ip running in a cluster
        """
        Log.info("Fetching data N/W info.")
        server_node_info = Conf.get(const.CONSUMER_INDEX, const.SERVER_NODE)
        data_nw_private_fqdn_list = []
        for machine_id, node_data in server_node_info.items():
            data_nw_private_fqdn_list.append(node_data["network"]["data"]["private_fqdn"])
        try:
            NetworkV().validate('connectivity', data_nw_private_fqdn_list)
        except VError as e:
            Log.error(f"Network Validation failed.{e}")
            raise CsmSetupError(f"Network Validation failed.{e}")
        return data_nw_private_fqdn_list

    def _set_db_host_addr(self):
        """
        Sets database hosts address in CSM config.
        :return:
        """
        es_host = self._get_es_hosts_info()
        try:
            Conf.set(const.DATABASE_CLI_INDEX, 'databases>es_db>config>hosts', es_host)
        except Exception as e:
            Log.error(f'Unable to set host address: {e}')
            raise CsmSetupError(f'Unable to set host address: {e}')

    def _set_s3_ldap_credentials(self):
        # read username's and password's for S3 and RMQ
        Log.info("Storing s3 credentials")
        open_ldap_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_S3_LDAP_USER])
        open_ldap_secret = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_S3_LDAP_SECRET])
        # Edit Current Config File.
        if open_ldap_user and open_ldap_secret:
            Log.info("Open-Ldap Credentials Copied to CSM Configuration.")
            Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_LOGIN}",
                     open_ldap_user)
            Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_PASSWORD}",
                     open_ldap_secret)

    def _set_csm_credentials(self):
        Log.info("CSM Credentials Copied to CSM Configuration.")
        csm_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CSM_USER])
        csm_pass = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CSM_SECRET])
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.CSM}>{const.PASSWORD}",
                 csm_pass)
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.PROVISIONER}>{const.PASSWORD}",
                 csm_pass)
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.CSM}>{const.USERNAME}",
                 csm_user)
        Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.PROVISIONER}>{const.USERNAME}",
                 csm_user)

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """
        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CORTXCLI_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        Conf.save(const.CORTXCLI_GLOBAL_INDEX)
        Conf.save(const.DATABASE_CLI_INDEX)
