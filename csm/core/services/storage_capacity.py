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
from cortx.utils.conf_store.conf_store import Conf
from csm.common.process import SimpleProcess,AsyncioSubprocess
from cortx.utils.log import Log
from csm.core.services.rgw.s3.utils import S3BaseService
from csm.core.blogic import const
from csm.common.errors import CsmInternalError, CsmError
from typing import Callable, Dict, Any
from csm.core.data.models.rgw import RgwError

class StorageCapacityService(S3BaseService):
    """
    Service for Get disk capacity details
    """

    def __init__(self, plugin):
        """
        Instantiation of StorageCapacityService.
        :param plugin: s3_iam_plugin object
        :returns: None
        """
        self.capacity_error = CapacityError()
        self._s3_iam_plugin = plugin

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


    async def request(self, session: ClientSession, method, url, expected_success_code):
        async with session.request(url=url, method=method) as resp:
            if resp.status != expected_success_code:
                self._create_error(resp.status, resp.reason)
                return self.capacity_error
            return await resp.json()

    async def get_cluster_data(self, data_filter=None):
        """
        Retrieve cluster data for specific resource or all resources.
        :param data_filter: Optional parameter indicate specific resource.
        :returns: cluster data or instance of error for negative scenarios.
        """

        url = Conf.get(const.CSM_GLOBAL_INDEX,const.CAPACITY_MANAGMENT_HCTL_SVC_ENDPOINT) + \
            Conf.get(const.CSM_GLOBAL_INDEX,const.CAPACITY_MANAGMENT_HCTL_CLUSTER_API)
        method = const.GET
        expected_success_code=200
        if data_filter:
            url = url + "/" + data_filter
        Log.info(f"Request {url} for cluster data")
        async with aiohttp.ClientSession() as session:
            try:
                response = await self.request(session, method, url, expected_success_code)
            except Exception as e:
                Log.error(f"Error in obtaining response from {url}: {e}")
                if "Cannot connect to" in str(e):
                    self._create_error(503, "Unable to connect to the service")
                    return self.capacity_error
                raise CsmInternalError(f"Error in obtaining response from {url}: {e}")

            return response

    async def get_capacity_usage(self, **request_body):
        """
        Retrieve capacity usage for specific user.
        :param user_id: user id whose capacity usage is fetching
        :returns: capacity usage or instance of error for negative scenarios.
        """
        uid = request_body.get(const.UID)
        Log.debug(f"Get Capcity usage of S3 IAM user by uid = {uid}")

        plugin_response =await self._s3_iam_plugin.execute(const.GET_CAPACITY_USAGE_OPERATION, **request_body)
        if isinstance(plugin_response, RgwError):
            self._handle_error(plugin_response)
        return plugin_response

        # response = {
        #     "stats": {
        #         "size": 250,
        #         "size_actual": 20480,
        #         "size_kb": 1,
        #         "size_kb_actual": 20,
        #         "num_objects": 5
        #     },
        #     "last_stats_sync": "2022-03-16T04:54:03.776590Z",
        #     "last_stats_update": "2022-03-16T04:54:58.047985Z"
        # }

    def _create_error(self, status: int, reason):
        """
        Converts a body of a failed query into orignal error object.
        :param status: HTTP Status code.
        :param body: parsed HTTP response (dict) with the error's decription.
        """
        Log.error(f"Create error body: {reason}")
        self.capacity_error.http_status = status
        self.capacity_error.message_id = reason
        self.capacity_error.message = reason

class CapacityError:
        """Class that describes a non-successful result"""
        http_status: int
        message_id: str
        message: str