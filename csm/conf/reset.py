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

from cortx.utils.log import Log
from csm.conf.setup import Setup, CsmSetupError
from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.service.service_handler import Service
from cortx.utils.data.db.consul_db.storage import CONSUL_ROOT


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
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DATABASE_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")
        self.disable_and_stop_service()
        self.directory_cleanup()
        await self.db_cleanup()
        await self._unsupported_feature_entry_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def disable_and_stop_service(self):
        service_obj = Service('csm_agent.service')
        if service_obj.is_enabled():
            Log.info("Disable csm_sgent.service")
            service_obj.disable()
        if service_obj.get_state().state == 'active':
            Log.info("Stop csm_sgent.service")
            service_obj.stop()

    def directory_cleanup(self):
        Log.info("Delete files and folders")
        files_directory_list = [
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE>firmware_store_path'),
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE>hotfix_store_path'),
            const.TMP_CSM,
            Conf.get(const.CSM_GLOBAL_INDEX, 'Log>log_path')
        ]

        for dir_path in files_directory_list:
            Log.info(f"Deleteing path :{dir_path}")
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
