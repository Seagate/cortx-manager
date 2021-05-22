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
from csm.common.fs_utils import FSUtils
from csm.conf.setup import CsmSetupError, Setup
from cortx.utils.data.db.consul_db.storage import CONSUL_ROOT

class Cleanup(Setup):
    """
    Delete all the CSM generated files and folders
    """

    def __init__(self):
        super(Cleanup, self).__init__()
        Log.info("Running Cleanup for CSM.")

    async def execute(self, command):
        """
        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DATABASE_CONF)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")

    def directory_cleanup(self):
        files_directory_list = [
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE>firmware_store_path'),
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE>hotfix_store_path'),
            const.TMP_CSM,
            const.RSYSLOG_PATH,
            Conf.get(const.CSM_GLOBAL_INDEX, 'Log>log_path'),
            Conf.get(const.CSM_GLOBAL_INDEX, 'SUPPORT_BUNDLE>bundle_path'),
            const.CSM_LOGROTATE_DEST,
            const.DEST_CRON_PATH,
            const.CSM_CONF_PATH,
        ]

        for dir_path in files_directory_list:
            Log.info(f"Deleteing path :{dir_path}")
            FSUtils.delete(dir_path)

    def load_db(self):
        """
        Load Database Provider from database.yaml
        :return:
        """
        Log.info("Loading Database Provider.")
        es_host = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>host')
        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        self._es_db_url = (f"http://{es_host}:{port}/")

        consul_host = Conf.get(const.DATABASE_INDEX, 'databases>consul_db>config>host')
        port = Conf.get(const.DATABASE_INDEX, 'databases>es_db>config>port')
        self._consul_db_url = (f"http://{consul_host}:{port}/v1/kv/{CONSUL_ROOT}/")

    def db_cleanup(self):
        self.load_db()

        for each_model in Conf.get(const.DATABASE_INDEX, "models"):
            if each_model.get('config').get('es_db'):
                collection_url = f"{self._es_db_url}{each_model.get('config').get('es_db').get('collection')}"
            else:
                collection_url = f"{self._es_db_url}{each_model.get('config').get('consul_db').get('collection')}"


