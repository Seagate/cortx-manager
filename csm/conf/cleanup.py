# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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
import glob
import ldap
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.core.providers.providers import Response
from cortx.utils.kv_store.error import KvError
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.conf.setup import CsmSetupError, Setup
from cortx.utils.validator.error import VError

class Cleanup(Setup):
    """
    Delete all the CSM generated files and folders
    """

    def __init__(self):
        super(Cleanup, self).__init__()
        Log.info("Triggering Cleanup for CSM.")

    async def execute(self, command):
        """
        :param command:
        :return:
        """
        try:
            Log.info("Loading configuration")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DATABASE_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        self._prepare_and_validate_confstore_keys()
        self.cleanup_ldap_config()
        await self._unsupported_feature_entry_cleanup()
        self.files_directory_cleanup()
        self.web_env_file_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}",
            const.KEY_ROOT_LDAP_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.OPENLDAP}>{const.ROOT}>{const.USER}",
            const.KEY_ROOT_LDAP_SCRET:f"{const.CORTX}>{const.SOFTWARE}>{const.OPENLDAP}>{const.ROOT}>{const.SECRET}"
        })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def files_directory_cleanup(self):
        files_directory_list = [
            const.RSYSLOG_PATH,
            const.CSM_LOGROTATE_DEST,
            const.DEST_CRON_PATH,
            const.CSM_CONF_PATH,
            Conf.get(const.CSM_GLOBAL_INDEX, 'Log>log_path')
        ]

        for dir_path in files_directory_list:
            Log.info(f"Deleteing path :{dir_path}")
            Setup._run_cmd(f"rm -rf {dir_path}")

    def web_env_file_cleanup(self):
       Log.info(f"Replacing {const.CSM_WEB_DIST_ENV_FILE_PATH}_tmpl " \
                                    f"{const.CSM_WEB_DIST_ENV_FILE_PATH}")
       Setup._run_cmd(f"cp -f {const.CSM_WEB_DIST_ENV_FILE_PATH}_tmpl " \
                                    f"{const.CSM_WEB_DIST_ENV_FILE_PATH}")

    def cleanup_ldap_config(self):
        """
        Cleanup LDAP Configurations
        """
        #Delete CortxAccount from LDAP
        self._delete_cortxaccount_from_ldap()
        #Delete cortxuser schema
        #ToDo: Add a validation based upon environment from confstore
        filelist = glob.glob('/etc/openldap/slapd.d/cn=config/cn=schema/*cortxuser.ldif')
        for schemafile in filelist:
            try:
                os.remove(schemafile)
            except Exception as e:
                Log.error(f"Failed to delete cortxuser schema: {e}")
                raise CsmSetupError("Failed to delete cortxuser schema.")
        #Delete permission attributes
        try:
            self._search_delete_permission_attr("olcDatabase={2}mdb,cn=config", "olcAccess")
        except Exception as e:
            Log.error(f"Failed to delete the ldap permission attributes: {e}")
            raise CsmSetupError("Failed to delete ldap permission attributes.")
        #Restart slapd service
        #ToDo: Add a validation based upon environment from confstore
        Setup._run_cmd('systemctl restart slapd')

    def _delete_cortxaccount_from_ldap(self):
        """
        Delete CortxAccount from LDAP
        """
        _ldapuser = self._fetch_ldap_root_user()
        _ldappasswd = self._fetch_ldap_root_password()
        if not _ldapuser:
            raise CsmSetupError("Failed to fetch LDAP root user")
        if not _ldappasswd:
            raise CsmSetupError("Failed to fetch LDAP root user password")
        base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BASE_DN_KEY}")

        csm_schema_version = Conf.get(const.CSM_GLOBAL_INDEX,
                                    const.LDAP_AUTH_CSM_SCHEMA_VERSION)
        bind_dn = const.LDAP_USER.format(_ldapuser,base_dn)
        self._delete_user_data(bind_dn, _ldappasswd, const.CORTXACCOUNTS_DN.format(csm_schema_version, base_dn))

    def _search_delete_permission_attr(self, dn, attr_to_delete):
        base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BASE_DN_KEY}")
        _bind_dn = "cn=admin,cn=config"
        _ldappasswd = self._fetch_ldap_root_password()
        try:
            self._connect_to_ldap_server(Setup._get_ldap_url(), _bind_dn, _ldappasswd)
        except Exception as e:
            Log.error(f'ERROR: LDAP connection failed, error: {str(e)}')
            raise CsmSetupError(f'ERROR: LDAP connection failed, error: {str(e)}')
        ldap_result_id = self._ldap_conn.search_s(dn, ldap.SCOPE_BASE, None, [attr_to_delete])
        olcAccess_list = ldap_result_id[0][1][attr_to_delete]
        # Count the number of records to be deleted.
        total_records_to_delete = sum("dc=csm,"+base_dn in record.decode('UTF-8')
                                        for record in olcAccess_list)
        # Below will perform delete operation
        while (total_records_to_delete > 0):
            ldap_result_id = self._ldap_conn.search_s(dn, ldap.SCOPE_BASE, None, [attr_to_delete])
            for result_dn, olcAccess_dict in ldap_result_id:
                if(olcAccess_dict):
                    for value in olcAccess_dict[attr_to_delete]:
                        if(value and (("dc=csm,"+base_dn in value.decode('UTF-8')))):
                            mod_attrs = [( ldap.MOD_DELETE, attr_to_delete, value )]
                            try:
                                self._ldap_conn.modify_s(dn, mod_attrs)
                                break
                            except Exception as e:
                                Log.error(f'Error while deleting attribute.{e}')
                                raise
            total_records_to_delete = total_records_to_delete - 1
        self._disconnect_from_ldap()

    async def _unsupported_feature_entry_cleanup(self):
        Log.info("Unsupported feature cleanup")
        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        _es_db_url = (f"http://localhost:{port}/")
        collection = "config"
        url = f"{_es_db_url}{collection}/_delete_by_query"
        payload = {"query": {"match": {"component_name": "csm"}}}
        Log.info(f"Deleting for collection:{collection} from es_db")
        await Setup.erase_index(collection, url, "post", payload)
