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

from csm.conf.setup import Setup, CsmSetupError
from csm.conf.uds import UDSConfigGenerator
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from cortx.utils.errors import DataAccessExternalError
from csm.core.blogic import const
from csm.common.payload import Yaml
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL

class Cleanup(Setup):
    """
    Cleanup all the Files and Folders generated by csm.
    """
    def __init__(self):
        super(Cleanup, self).__init__()
        Log.info("Running Cleanup for CSM.")
        self._db = None

    async def execute(self, command):
        database_cleanup = (command.options.get("database_cleanup",
                                                False) == 'true')
        try:
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, f"yaml://{const.DATABASE_CONF}")
        except KvError as e:
            Log.error(f"Loading csm.conf to conf store failed {e}")
            raise CsmSetupError("Failed to Load CSM Configuration File.")
        self._log_cleanup()
        UDSConfigGenerator.delete()
        if database_cleanup:
            self.load_db()
            self.es_cleanup()
            self.consul_cleanup()
        self.Config.delete()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _log_cleanup(self):
        """
        Delete all logs
        """
        Log.info("Delete all logs")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        Setup._run_cmd("rm -rf " +log_path)

    def load_db(self):
        """
        Load Database Provider from database.yaml
        :return:
        """
        Log.info("Loading Database Provider.")
        conf = GeneralConfig(Yaml(const.DATABASE_CLI_CONF).load())
        self._db = DataBaseProvider(conf)

    def _db_cleanup(self):
        """
        :return:
        """
        self._es_host = Conf.get(const.DATABASE_INDEX,
                                 "databases>es_db>config>host")
        for each_model in Conf.get(const.DATABASE_INDEX, "models"):
            if each_model.get("database") == "es_db":
                self._es_cleanup(each_model.get("collection"))
            if each_model.get("database") == "consul_db":
                self._es_cleanup(each_model.get("collection"))

    def _es_cleanup(self, es_collection_name):
        """
        Clean up all the CSM Elasticsearch Data.
        :param es_collection_name: Elasticsearch Collection Name to be Deleted.
        :return:
        """
        Log.info(f"Cleaning up Collection {es_collection_name}")
        pass

    def consul_cleanup(self, consul_collection_name):
        """
        Cleanup all the CSM Consul Data.
        :param consul_collection_name: Consul Collection Name to be Deleted.
        :return:
        """
        Log.info(f"Cleaning up Collection {consul_collection_name}")
        pass

