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
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DB_SOURCE_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        self._prepare_and_validate_confstore_keys()
        self._set_deployment_mode()
        self._set_secret_string_for_decryption()
        self._set_cluster_id()
        self._set_db_host_addr()
        self._set_fqdn_for_nodeid()
        self._set_s3_ldap_credentials()
        self._set_password_to_csm_user()
        if not self._replacement_node_flag:
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
            const.KEY_CSM_SECRET:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.SECRET}"
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
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CSM}>password_decryption_key",
                    self.conf_store_keys[const.KEY_CSM_SECRET].split('>')[0])
        Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>password_decryption_key",
                    self.conf_store_keys[const.KEY_S3_LDAP_SECRET].split('>')[0])

    def _set_cluster_id(self):
        Log.info("Setting up cluster id")
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        if not cluster_id:
            raise CsmSetupError("Failed to fetch cluster id")
        Conf.set(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY, cluster_id)

    def _set_fqdn_for_nodeid(self):
        Log.info("Setting hostname to server node name")
        server_node_info = Conf.get(const.CONSUMER_INDEX, const.SERVER_NODE)
        Log.debug(f"Server node information: {server_node_info}")
        for machine_id, node_data in server_node_info.items():
            hostname = node_data.get(const.HOSTNAME, const.NAME)
            node_name = node_data.get(const.NAME)
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.MAINTENANCE}>{node_name}",f"{hostname}")

    def _get_data_nw_info(self):
        """
        Obtains minion data network info.

        :param machine_id: Minion id.
        """
        Log.info("Fetching data N/W info.")
        data_nw_private_fqdn = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_DATA_NW_PRIVATE_FQDN])
        try:
            NetworkV().validate('connectivity', [data_nw_private_fqdn])
        except VError as e:
            Log.error(f"Network Validation failed.{e}")
            raise CsmSetupError(f"Network Validation failed.{e}")
        return data_nw_private_fqdn

    def _set_db_host_addr(self):
        """
        Sets database backend host address in CSM config.

        :param backend: Databased backend. Supports Elasticsearch('es'), Consul ('consul').
        :param addr: Host address.
        """
        addr = self._get_data_nw_info()
        try:
            Conf.set(const.DATABASE_INDEX, 'databases>es_db>config>host', addr)
            Conf.set(const.DATABASE_INDEX, 'databases>consul_db>config>host', addr)
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
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_LOGIN}",
                     open_ldap_user)
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_PASSWORD}",
                     open_ldap_secret)

    def _set_password_to_csm_user(self):
        if not self._is_user_exist():
            raise CsmSetupError(f"{self._user} not created on system.")
        Log.info("Fetch decrypted password.")
        _password = self._fetch_csm_user_password(decrypt=True)
        if not _password:
            Log.error("CSM Password Not Available.")
            raise CsmSetupError("CSM Password Not Available.")
        _password = crypt.crypt(_password, "22")
        Setup._run_cmd(f"usermod -p {_password} {self._user}")

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

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        self.store_encrypted_password()
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")
