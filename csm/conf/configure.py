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
            self.Config.load()
            UDSConfigGenerator.apply(uds_public_ip=uds_public_ip)
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
