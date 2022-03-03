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
        await self._unsupported_feature_entry_cleanup()
        self.files_directory_cleanup()
        self.web_env_file_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}"
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

    async def _unsupported_feature_entry_cleanup(self):
        Log.info("Unsupported feature cleanup")
        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        _es_db_url = (f"http://localhost:{port}/")
        collection = "config"
        url = f"{_es_db_url}{collection}/_delete_by_query"
        payload = {"query": {"match": {"component_name": "csm"}}}
        Log.info(f"Deleting for collection:{collection} from es_db")
        await Setup.erase_index(collection, url, "post", payload)
