# CORTX-CSM: CORTX Management web and CLI interface.
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

import time
import ldap
from ldap.ldapobject import SimpleLDAPObject
from cortx.utils.log import Log
from csm.conf.setup import Setup, CsmSetupError
from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.service.service_handler import Service
from cortx.utils.data.db.consul_db.storage import CONSUL_ROOT
from cortx.utils.validator.error import VError

class Reset(Setup):
    """
    Reset csm Configuration.
    """
    def __init__(self):
        super(Reset, self).__init__()
        Log.info("Triggering csm_setup reset")

    async def execute(self, command):
        """
        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DATABASE_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")
        self._prepare_and_validate_confstore_keys()
        # self.disable_and_stop_service()
        # self.directory_cleanup()
        # await self.db_cleanup()
        # await self._unsupported_feature_entry_cleanup()
        self._delete_csm_ldap_data()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}",
            const.KEY_ROOT_LDAP_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.OPENLDAP}>{const.ROOT}>{const.USER}",
            const.KEY_ROOT_LDAP_SECRET:f"{const.CORTX}>{const.SOFTWARE}>{const.OPENLDAP}>{const.ROOT}>{const.SECRET}"
        })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def disable_and_stop_service(self):
        for each_service in [const.CSM_AGENT_SERVICE, const.CSM_WEB_SERVICE]:
            try:
                service_obj = Service(each_service)
                if service_obj.is_enabled():
                    Log.info(f"Disabling {each_service}")
                    service_obj.disable()
                if service_obj.get_state().state == 'active':
                    Log.info(f"Stopping {each_service}")
                    service_obj.stop()

                Log.info(f"Checking if {each_service} stopped.")
                for count in range(0, 10):
                    if not service_obj.get_state().state == 'active':
                        break
                    time.sleep(2**count)
                if service_obj.get_state().state == 'active':
                    Log.error(f"{each_service} still active")
                    raise CsmSetupError(f"{each_service} still active")
            except Exception as e:
                Log.warn(f"{each_service} not available: {e}")

    def directory_cleanup(self):
        Log.info("Deleting files and folders")
        files_directory_list = [
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE>firmware_store_path'),
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE>hotfix_store_path'),
            const.TMP_CSM,
            Conf.get(const.CSM_GLOBAL_INDEX, 'Log>log_path')
        ]

        for dir_path in files_directory_list:
            Log.info(f"Deleting path :{dir_path}")
            Setup._run_cmd(f"rm -rf {dir_path}")

    async def db_cleanup(self):

        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        self._es_db_url = (f"http://localhost:{port}/")
        port = Conf.get(const.DATABASE_INDEX, 'databases>consul_db>config>port')
        self._consul_db_url = (f"http://localhost:{port}/v1/kv/{CONSUL_ROOT}/")

        for each_model in Conf.get(const.DATABASE_INDEX, "models"):
            if each_model.get('config').get('es_db'):
                db = "es_db"
                collection = f"{each_model.get('config').get('es_db').get('collection')}"
                url = f"{self._es_db_url}{collection}"
            else:
                db = "consul_db"
                collection = f"{each_model.get('config').get('consul_db').get('collection')}"
                url = f"{self._consul_db_url}{collection}?recurse"

            Log.info(f"Deleting for collection:{collection} from {db}")
            await self.erase_index(collection, url, "delete")

    async def _unsupported_feature_entry_cleanup(self):
        collection = "config"
        url = f"{self._es_db_url}{collection}/_delete_by_query"
        payload = {"query": {"match": {"component_name": "csm"}}}
        Log.info(f"Deleting for collection:{collection} from es_db")
        await self.erase_index(collection, url, "post", payload)

    async def erase_index(self, collection, url, method, payload=None):
        Log.info(f"Url: {url}")
        try:
            response, headers, status = await Setup.request(url, method, payload)
            if status != 200:
                Log.error(f"Index {collection} Could Not Be Deleted.")
                Log.error(f"Response --> {response}")
                Log.error(f"Status Code--> {status}")
                return
        except Exception as e:
            Log.warn(f"Failed at deleting for {collection}")
            Log.warn(f"{e}")
        Log.info(f"Index {collection} Deleted.")

    def _delete_csm_ldap_data(self):
        self._ldapuser = self._fetch_ldap_root_user()
        self._ldappasswd = self._fetch_ldap_root_password()
        if not self._ldapuser:
            raise CsmSetupError("Failed to fetch LDAP root user")
        if not self._ldappasswd:
            raise CsmSetupError("Failed to fetch LDAP root user password")
        self._delete_ldap_data()

    def _delete_ldap_data(self):
        """
        Delete all cortx users data entries from ldap.
        """
        try:
            Log.info('Deletion of ldap data started.')
            self._connect_to_ldap_server()
            for entry in const.DELETE_LDAP_RECORDS:
                Log.info(' deleting all entries from {entry} & its sub-ordinate tree')
                try:
                    self._ldap_delete_recursive(self._ldap_conn, entry)
                except ldap.NO_SUCH_OBJECT:
                # If no entries found in ldap for given dn
                    pass
            self._disconnect_from_ldap()
            Log.info('Deletion of ldap data completed successfully.')
        except Exception as e:
            if self._ldap_conn:
                self._disconnect_from_ldap()
            Log.error(f'ERROR: Failed to delete ldap data, error: {str(e)}')
            raise CsmSetupError(f'Failed to delete ldap data, error: {str(e)}')

    def _ldap_delete_recursive(self, ldap_conn: SimpleLDAPObject, base_dn: str):
        """
        Delete all objects and its subordinate entries from ldap.
        """
        l_search = ldap_conn.search_s(base_dn, ldap.SCOPE_ONELEVEL)
        for dn, _ in l_search:
            if not dn == base_dn:
                self._ldap_delete_recursive(ldap_conn, dn)
                ldap_conn.delete_s(dn)
