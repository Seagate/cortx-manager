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

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.core.providers.providers import Response
from cortx.utils.kv_store.error import KvError
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.conf.setup import CsmSetupError, Setup

class Cleanup(Setup):
    """
    Delete all the CSM generated files,folders, Configs and Non user collected data.
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
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DATABASE_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        if command.options.get("pre-factory"):
            # Pre-Factory: Cleanup the system and take to 
            #               pre-factory (Postinstall) stage
            self._replace_csm_service_file()
            self._service_user_cleanup()
        await self._unsupported_feature_entry_cleanup()
        self.files_directory_cleanup()
        self.web_env_file_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _replace_csm_service_file(self):
        '''
        Service file cleanup
        '''
        Log.info(f"Replace service file.")
        Setup._run_cmd(f"cp -f {const.CSM_AGENT_SERVICE_FILE_SRC_PATH} /etc/systemd/system/")

    def _service_user_cleanup(self):
        '''
        Remove service user if system deployed in dev mode.
        '''
        self._user = Conf.get(const.CSM_GLOBAL_INDEX, f"{const.CSM}>{const.USERNAME}")
        if Conf.get(const.CSM_GLOBAL_INDEX, const.KEY_DEPLOYMENT_MODE) == const.DEV and \
                    self._is_user_exist():
            Log.info(f"Remove Service user: {self._user}")
            Setup._run_cmd(f"userdel -f {self._user}")

    def files_directory_cleanup(self):
        '''
        Cleanup CSM config and Remove Log directory
        '''
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
        '''
        Web config (.env) Cleanup
        '''
        Log.info(f"Replacing {const.CSM_WEB_DIST_ENV_FILE_PATH}_tmpl " \
                                        f"{const.CSM_WEB_DIST_ENV_FILE_PATH}")
        Setup._run_cmd(f"cp -f {const.CSM_WEB_DIST_ENV_FILE_PATH}_tmpl " \
                                    f"{const.CSM_WEB_DIST_ENV_FILE_PATH}")

    async def _unsupported_feature_entry_cleanup(self):
        '''
        Remove CSM Unsupported features entries
        '''
        Log.info("Unsupported feature cleanup")
        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        _es_db_url = (f"http://localhost:{port}/")
        collection = "config"
        url = f"{_es_db_url}{collection}/_delete_by_query"
        payload = {"query": {"match": {"component_name": "csm"}}}
        Log.info(f"Deleting for collection:{collection} from es_db")
        await Setup.erase_index(collection, url, "post", payload)
