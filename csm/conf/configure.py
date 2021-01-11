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

    def execute(self, command):
        """

        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get("config_url"))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CORTXCLI_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        if command.options.get(const.DEBUG) == 'true':
            Log.info("Running Csm Setup for Development Mode.")
            self._debug_flag = True
        try:
            uds_public_ip = command.options.get('uds_public_ip')
            if uds_public_ip is not None:
                ip_address(uds_public_ip)
            if not self._replacement_node_flag:
                self.create()
            UDSConfigGenerator.apply(uds_public_ip=uds_public_ip)
            Configure._set_node_id()
            minion_id = Configure._get_minion_id()
            data_nw = Configure._get_data_nw_info(minion_id)
            Configure._set_db_host_addr('consul',
                                  data_nw.get('roaming_ip', 'localhost'))
            Configure._set_db_host_addr('es', data_nw.get('pvt_ip_addr', 'localhost'))
        except Exception as e:
            import traceback
            Log.error(f"csm_setup config failed. Error: {e} - {str(traceback.print_exc())}")
            raise CsmSetupError(f"csm_setup config failed. Error: {e} - {str(traceback.print_exc())}")

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """
        Log.error("Create the CSM Conf File on Required Location.")
        if self._debug_flag:
            Log.info("Setting Dev Mode Key in Csm Conf")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}", const.DEV)
        else:
            Configure.store_encrypted_password()
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")

    @staticmethod
    def store_encrypted_password():
        """
        :return:
        """
        # read username's and password's for S3 and RMQ
        Log.info("Storing Encrypted Password")
        # TODO:  Change Keys Here.
        open_ldap_credentials = Conf.get(const.CONSUMER_INDEX, const.OPENLDAP)
        # Edit Current Config File.
        if open_ldap_credentials and isinstance(open_ldap_credentials, dict):
            Log.info("Openldap Credentials Copied to CSM Configuration.")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_LOGIN}",
                    open_ldap_credentials.get(const.IAM_ADMIN, {}).get(
                        const.USER))
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.S3}>{const.LDAP_PASSWORD}",
                     open_ldap_credentials.get(const.IAM_ADMIN, {}).get(
                         const.SECRET))
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
        # TODO:  Change Keys Here.
        cluster_id = Conf.get(const.CONSUMER_INDEX, const.CLUSTER_ID)
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
            raise CsmSetupError(f"Unable to fetch system node ids info.")

    @staticmethod
    def _get_minion_id():
        """
        Obtains current minion id. If it cannot be obtained, returns default node #1 id.
        """
        Log.info("Fetch Minion Id.")
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
        Log.info("Fetch data N/W info.")
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
