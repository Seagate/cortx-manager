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

import aiohttp
from aiohttp.client import ClientSession
from csm.common.process import SimpleProcess,AsyncioSubprocess
from cortx.utils.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.common.errors import CsmInternalError, CsmError
from typing import Callable, Dict, Any
from cortx.utils.conf_store.conf_store import Conf


class StorageCapacityService(ApplicationService):
    """
    Service for Get disk capacity details
    """

    @staticmethod
    def _integer_to_human(capacity: int, unit:str, round_off_value=const.DEFAULT_ROUNDOFF_VALUE) -> str:
        """
        Method to dynamically convert byte data in KB/MB/GB ... YB.

        :param capacity: Disk size in bytes :type: int
        :return: :type: str
        """
        capacity_float = float(capacity)
        for each_unit in const.UNIT_LIST:
            if const.UNIT_LIST.index(each_unit) <= const.UNIT_LIST.index(unit):
                capacity_float = capacity_float / 1024
                # if capacity_float / 100 < 10:
            else:
                break

        return round(capacity_float, round_off_value)

    @Log.trace_method(Log.DEBUG)
    async def get_capacity_details(self, unit=const.DEFAULT_CAPACITY_UNIT, round_off_value=const.DEFAULT_ROUNDOFF_VALUE) -> Dict[str, Any]:
        """
        This method will return system disk details as per command

        :return: dict
        """

        def convert_to_format(value: int, unit: str ,round_off_value:int) -> Any:
            if unit.upper()==const.DEFAULT_CAPACITY_UNIT:
                # keep original format (i.e., integer)
                return value
            return StorageCapacityService._integer_to_human(value, unit.upper(), round_off_value)

        try:
            process = AsyncioSubprocess(const.FILESYSTEM_STAT_CMD)
            stdout, stderr, rc = await process.run()
        except Exception as e:
            raise CsmInternalError(f"Error in command execution, command : {e}")
        if not stdout:
            raise CsmInternalError(f"Failed to process command : {stderr.decode('utf-8')}"
                                   f"-{stdout.decode('utf-8')}")
        Log.debug(f'{const.FILESYSTEM_STAT_CMD} command output stdout:{stdout}')
        console_output = json.loads(stdout.decode('utf-8'))
        capacity_info = console_output.get('filesystem',{}).get('stats',{})

        if not capacity_info:
            raise CsmInternalError("System storage details not available.")
        if int(capacity_info[const.TOTAL_SPACE]) <= 0:
            raise CsmInternalError("Total storage space cannot be zero", message_args=capacity_info)
        formatted_output = {}
        formatted_output[const.SIZE] = convert_to_format(int(capacity_info[const.TOTAL_SPACE]),unit,round_off_value)
        formatted_output[const.USED] = convert_to_format(
            int(capacity_info[const.TOTAL_SPACE] - capacity_info[const.FREE_SPACE]),unit,round_off_value)
        formatted_output[const.AVAILABLE] = convert_to_format(int(capacity_info[const.FREE_SPACE]),unit,round_off_value)
        formatted_output[const.USAGE_PERCENTAGE] = round((((int(capacity_info[const.TOTAL_SPACE]) -
                                                             int(capacity_info[const.FREE_SPACE])) /
                                                             int(capacity_info[const.TOTAL_SPACE])) * 100),round_off_value)
        formatted_output[const.UNIT] = unit
        return formatted_output

    async def request(self, session: ClientSession, method, url):
        async with session.request(url=url, method=method) as resp:
            return await resp.json(), resp.status

    async def get_cluster_data(self, data_filter=None):
        #TODO: Use data_filter for filtering out the data, once integrated in hctl api
        url = Conf.get(const.CSM_GLOBAL_INDEX,const.CAPACITY_MANAGMENT_HCTL_SVC_ENDPOINT) + \
            Conf.get(const.CSM_GLOBAL_INDEX,const.CAPACITY_MANAGMENT_HCTL_CLUSTER_API)
        method = const.GET
        if data_filter:
            url = url+data_filter
        Log.info(f"Request {url} for cluster data")
        async with aiohttp.ClientSession() as session:
            try:
                response, status = await self.request(session, method, url)
            except Exception as e:
                Log.error(f"Error in obtaining response from {url}: {e}")
                raise CsmInternalError(f"Error in obtaining response from {url}: {e}")
        Log.debug(f"Response: {response}, Status:{status} for url :{url}")
        return response, status
