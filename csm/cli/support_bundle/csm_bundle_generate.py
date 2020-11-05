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
import errno
from csm.core.blogic import const
from csm.common.payload import Yaml, Tar, Json
from csm.common.conf import Conf
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.common.errors import CsmError
from cortx.utils.log import Log
from csm.core.services.alerts import AlertRepository

class CSMBundle:
    """
    ThiS Class generates the Support Bundle for Component CSM.

    Currently Included Files in CSM Support Bundle:-
    1) cortxcli.log -- Logs for CLI .
    2) csm_agent.log -- Logs for CSM Backend Agent.
    3) csm_setup.log -- Logs generated during setup for CSM Component.
    """

    @staticmethod
    async def init(command):
        """
        This method will generate bundle for CSM and include the logs in it.
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        # Read Config to Fetch Log File Path
        csm_log_directory_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path")
        uds_log_directory_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.uds_log_path")
        es_cluster_log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.es_cluster_log_path")
        es_gc_log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.es_gc_log_path")
        es_indexing_log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.es_indexing_log_path")
        es_search_log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.es_search_log_path")
        # Creates CSM Directory
        path = command.options.get("path")
        bundle_id = command.options.get("bundle_id")
        component_name = command.options.get("component", "csm")
        component_data = {"csm": [csm_log_directory_path],
                          "uds": [uds_log_directory_path],
                          "elasticsearch": [es_cluster_log_path,
                                            es_gc_log_path,
                                            es_indexing_log_path,
                                            es_search_log_path]}
        if component_name == "alerts":
            alerts_filename = Conf.get(const.CSM_GLOBAL_INDEX, "SUPPORT_BUNDLE.alerts_filename")
            # Fetch alerts for support bundle.
            alerts_data = await CSMBundle.fetch_and_save_alerts()
            alerts_file_path = os.path.join(path, alerts_filename)
            obj_alert_json = Json(alerts_file_path)
            obj_alert_json.dump(alerts_data)
            component_data["alerts"] = [alerts_file_path]

        temp_path = os.path.join(path, component_name)
        os.makedirs(temp_path, exist_ok = True)
        # Generate Tar file for Logs Folder.
        tar_file_name = os.path.join(temp_path, f"{component_name}_{bundle_id}.tar.gz")
        if all(map(os.path.exists, component_data[component_name])):
            Tar(tar_file_name).dump(component_data[component_name])
        else:
            raise CsmError(rc = errno.ENOENT,
                           desc = f"Component log missing: {component_data[component_name]}")

    @staticmethod
    async def fetch_and_save_alerts():
        """
        Fetches the alerts from es db and creates a json file
        :param command: Csm_cli Command Object :type: command
        :return: None
        """
        alerts =[]
        try:
            conf = GeneralConfig(Yaml(const.DATABASE_CLI_CONF).load())
            db = DataBaseProvider(conf)
            repo = AlertRepository(db)
            alerts = await repo.fetch_alert_for_support_bundle()
        except Exception as ex:
            Log.error(f"Error occured while fetching alerts: {ex}")
            alerts = [{"Error": "Internal error: Could not fetch alerts."}]
        return alerts
