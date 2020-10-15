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
from csm.core.blogic import const
from csm.common.payload import Yaml, Tar
from csm.common.conf import Conf

class CSMBundle:
    """
    ThiS Class generates the Support Bundle for Component CSM.

    Currently Included Files in CSM Support Bundle:-
    1) csmcli.log -- Logs for CLI .
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
        log_directory_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path")
        # Creates CSM Directory
        path = command.options.get("path")
        bundle_id = command.options.get("bundle_id")
        component_name = command.options.get("component", "csm")
        component_data = {"csm": [log_directory_path],
                          "uds": ["/var/log/uds"],
                          "elasticsearch": ["/var/log/elasticsearch/elasticsearch_cluster.log"]}
        temp_path = os.path.join(path, component_name)
        os.makedirs(temp_path, exist_ok = True)
        # Generate Tar file for Logs Folder.
        tar_file_name = os.path.join(path, f"{component_name}_{bundle_id}.tar.gz")
        Tar(tar_file_name).dump(component_data[component_name])


