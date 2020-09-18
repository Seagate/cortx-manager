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

import json
from csm.common.process import SimpleProcess,AsyncioSubprocess
from cortx.utils.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.common.errors import CsmInternalError, CsmError
from typing import Callable, Dict, Any

class StorageCapacityService(ApplicationService):
    def __init__(self, provisioner):
        self._provisioner = provisioner
    """
    Service for Get disk capacity details
    """

    @staticmethod
    def _integer_to_human(capacity: int) -> str:
        """
        Method to dynamically convert byte data in KB/MB/GB ... YB.

        :param capacity: Disk size in bytes :type: int
        :return: :type: str
        """
        capacity_float = float(capacity)
        for unit in const.UNIT_LIST:
            capacity_float = capacity_float / 1024
            if capacity_float / 100 < 10:
                break

        return f'{round(capacity_float, 2)} {unit}'

    @Log.trace_method(Log.DEBUG)
    async def get_capacity_details(self, format: str = 'integer') -> Dict[str, Any]:
        """
        This method will return system disk details as per command
        :param format: Capacity format; integers by default, use 'human' for human-readable.
        :return: dict
        """

        def convert_to_format(value: int) -> Any:
            if format.lower() == 'human':
                return StorageCapacityService._integer_to_human(value)
            else:
                # keep original format (i.e., integer)
                return value

        try:
            process = AsyncioSubprocess(const.FILESYSTEM_STAT_CMD)
            stdout, stderr = await process.run()
        except Exception as e:
            raise CsmInternalError(f"Error in command execution command : {e}")
        if not stdout:
            raise CsmInternalError(f"Failed to process command : {stderr.decode('utf-8')}"
                                   f"-{stdout.decode('utf-8')}")
        Log.debug(f'{const.FILESYSTEM_STAT_CMD} command output stdout:{stdout}')
        console_output = json.loads(stdout.decode('utf-8'))
        capacity_info = console_output.get('filesystem',{}).get('stats',{})
        if not capacity_info:
            raise CsmInternalError(f"System storage details not available.")
        formatted_output = {}
        formatted_output[const.SIZE] = convert_to_format(int(capacity_info[const.TOTAL_SPACE]))
        formatted_output[const.USED] = convert_to_format(
            int(capacity_info[const.TOTAL_SPACE] - capacity_info[const.FREE_SPACE]))
        formatted_output[const.AVAILABLE] = convert_to_format(int(capacity_info[const.FREE_SPACE]))
        formatted_output[const.USAGE_PERCENTAGE] = str(round((((int(capacity_info[const.TOTAL_SPACE]) -
                                                             int(capacity_info[const.FREE_SPACE])) / 
                                                             int(capacity_info[const.TOTAL_SPACE])) * 100),2)) + ' %'       
        return formatted_output
