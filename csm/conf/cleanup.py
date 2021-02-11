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

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.log import Log
from cortx.utils.data.db.consul_db.storage import CONSUL_ROOT

from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.payload import Yaml
from csm.conf.setup import CsmSetupError, Setup
from csm.conf.uds import UDSConfigGenerator
from csm.core.blogic import const
from csm.core.providers.providers import Response

class Cleanup(Setup):
    """
    Cleanup all the Files and Folders generated by csm.
    """

    def __init__(self):
        super(Cleanup, self).__init__()
        Log.info("Running Cleanup for CSM.")
        self._db = ""
        self._es_db_url = ""
        self._consul_db_url = ""

    async def execute(self, command):
        try:
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, f"yaml://{const.DATABASE_CONF}")
        except KvError as e:
            Log.error(f"Loading csm.conf to conf store failed {e}")
            raise CsmSetupError("Failed to Load CSM Configuration File.")
        await self._db_cleanup()
        self._log_cleanup()
        self.directory_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _log_cleanup(self):
        """
        Delete all logs
        """
        Log.info("Delete all logs")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        Setup._run_cmd("rm -rf " + log_path)

    def load_db(self):
        """
        Load Database Provider from database.yaml
        :return:
        """
        Log.info("Loading Database Provider.")
        conf = Yaml(const.DATABASE_CONF).load()
        es_db_details = conf.get("databases", {}).get("es_db")
        consul_details = conf.get("databases", {}).get("consul_db")
        self._es_db_url = (f"http://{es_db_details['config']['host']}:"
                           f"{es_db_details['config']['port']}/")
        self._consul_db_url = (f"http://{consul_details['config']['host']}:"
                    f"{consul_details['config']['port']}/v1/kv/{CONSUL_ROOT}")

    async def _db_cleanup(self):
        """
        Clean Data Base Collection As per Logic.
        :return:
        """
        self.load_db()
        for each_model in Conf.get(const.DATABASE_INDEX, "models"):
            await self.erase_index(each_model.get("config", {}))

    async def erase_index(self, collection_details):
        """
        Clean up all the CSM Elasticsearch Data for provided Index.
        :param collection_details: Collection Details to be Deleted.
        :return: None
        """
        url = None
        collection = ""
        if collection_details.get("es_db"):
            collection = collection_details.get('consul_db', {}).get(
                'collection')
            url = f"{self._es_db_url}{collection}"
        else:
            collection = collection_details.get('consul_db', {}).get(
                'collection')
            url = f"{self._consul_db_url}/{collection}/?recurse"

        Log.info(f"Attempting Deletion of Collection {collection}")
        text, headers, status = await self.request(url, "delete")
        if status != 200:
            Log.error(f"Index {collection} Could Not Be Deleted.")
            Log.error(f"Response --> {text}")
            Log.error(f"Status Code--> {status}")
            return
        Log.info(f"Index {collection} Deleted.")

    def selective_cleanup(self, collection_details):
        """
        Cleanup all the CSM Consul Data.
        :param collection_details: Consul Collection Name to be Deleted.
        :return:
        """
        Log.info(f"Cleaning up Collection {collection_details}")
        # TODO: Implement Selective Deletion.

    def directory_cleanup(self):
        """
        Delete local Directories as Follows:
        /etc/csm
        /var/log/seagate/csm
        /var/log/seagate/support_bundle
        /tmp/csm
        /tmp/hotfix
        :return:
        """
        self.Config.delete()
        for each_directory in const.CLEANUP_DIRECTORIES:
            Log.info(f"Deleting Directory {each_directory}")
            Setup._run_cmd(f"rm -rf {each_directory}")
