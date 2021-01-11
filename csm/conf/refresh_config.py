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
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kvstore.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const

class RefreshConfig(Setup):
    """

    """
    def __init__(self):
        super(RefreshConfig, self).__init__()
        Log.info("Triggering csm_setup refresh_config")
        self._debug_flag = False

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
            node_id = self._get_faulty_node_uuid()
            self._resolve_faulty_node_alerts(node_id)
            Log.info(
                f"Resolved and acknowledged all the faulty node : {node_id} alerts")
        except Exception as e:
            Log.error(f"csm_setup refresh_config failed. Error: {e}")
            raise CsmSetupError(f"csm_setup refresh_config failed. Error: {e}")

    @classmethod
    def _get_faulty_node_uuid(self):
        """
        This method will get the faulty node uuid from provisioner.
        This uuid will be used to resolve the faulty alerts for replaced node.
        """
        faulty_minion_id = ''
        faulty_node_uuid = ''
        try:
            Log.info("Getting faulty node id")
            faulty_minion_id_cmd = "cluster:replace_node:minion_id"
            faulty_minion_id = SaltWrappers.get_salt_call(const.PILLAR_GET, faulty_minion_id_cmd)
            if not faulty_minion_id:
                Log.warn("Fetching faulty node minion id failed.")
                raise CsmSetupError("Fetching faulty node minion failed.")
            faulty_node_uuid = SaltWrappers.get_salt(const.GRAINS_GET, 'node_id', faulty_minion_id)
            if not faulty_node_uuid:
                Log.warn("Fetching faulty node uuid failed.")
                raise CsmSetupError("Fetching faulty node uuid failed.")
            return faulty_node_uuid
        except Exception as e:
            Log.warn(f"Fetching faulty node uuid failed. {e}")
            raise CsmSetupError(f"Fetching faulty node uuid failed. {e}")

    def _resolve_faulty_node_alerts(self, node_id):
        """
        This method resolves all the alerts for a fault replaced node.
        """
        try:
            Log.info("Resolve faulty node alerts")
            conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
            db = DataBaseProvider(conf)
            alerts = []
            if db:
                loop = asyncio.get_event_loop()
                alerts_repository = AlertRepository(db)
                alerts = loop.run_until_complete\
                    (alerts_repository.retrieve_unresolved_by_node_id(node_id))
                if alerts:
                    for alert in alerts:
                        if not const.ENCLOSURE in alert.module_name:
                            alert.acknowledged = AlertModel.acknowledged.to_native(True)
                            alert.resolved = AlertModel.resolved.to_native(True)
                            loop.run_until_complete(alerts_repository.update(alert))
                else:
                    Log.warn(f"No alerts found for node id: {node_id}")
            else:
                Log.error("csm_setup refresh_config failed. Unbale to load db.")
                raise CsmSetupError("csm_setup refresh_config failed. Unbale to load db.")
        except Exception as ex:
            Log.error(f"Refresh Context: Resolving of alerts failed. {ex}")
            raise CsmSetupError(f"Refresh Context: Resolving of alerts failed. {ex}")

