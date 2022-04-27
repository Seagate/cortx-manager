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
from csm.common.services import ApplicationService
from csm.core.services.rgw.s3.utils import S3BaseService
from csm.core.blogic import const
from csm.common.errors import CsmInternalError, CsmError
from typing import Callable, Dict, Any
from csm.core.data.models.rgw import RgwError
from csm.common.errors import CsmResourceNotAvailable

class StorageCapacityService(ApplicationService):
    """
    Service for Get disk capacity details
    """

    def __init__(self):
        self.capacity_error = CapacityError()

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

class StorageCapacityUsageService(S3BaseService):
    """
    Service for Get disk capacity details
    """

    def __init__(self, plugin):
        """
        Instantiation of StorageCapacityService.
        :param plugin: s3_iam_plugin object
        :returns: None
        """
        self._s3_iam_plugin = plugin

    async def create_response_body(self, resource, plugin_response):
        # Map response from rgw to Csm response body
        # Sample Responce for RGW
        plugin_response = {
            "system": {
                "node": {
                    "total": 1111,
                    "available": 1111,
                    "free": 1111,
                    "degraded": {}
                }
            },
            "s3":
            {
                "user":{
                    "id": "user id",
                    "size": 0000,
                    "actual_size": 0000,
                    "num_objects": 0
                }
            }
        }

        # TODO: Need to discuss
        # what are the expected resource? will it always inner level like user bucket node etc.
        # or can it be on first level resource like system s3 etc.

        resp = {}
        # Check on First Level, if available then return dict with Key= resource and Value = resp[key]
        if resource in plugin_response.keys():
            resp[resource] = plugin_response[resource]
            return resp
        else:
            for first_level_resource in plugin_response.keys():
                # else Check on Inner level of Each Resource,
                if resource in plugin_response[first_level_resource].keys():
                    # If resource found in sec
                    # {key= firstLevel_resource, value = dict{key= resource, value=resp[first_level][resource]} }
                    resp[first_level_resource] = {resource : plugin_response[first_level_resource][resource]}
                    return resp
        # else Resource does not exist
        raise CsmResourceNotAvailable("Request resource is not available")

    async def get_capacity_usage(self, **request_body):
        """
        Retrieve capacity usage for specific user.
        :param user_id: user id whose capacity usage is fetching
        :returns: capacity usage or instance of error for negative scenarios.
        """
        resource_id = request_body.get(const.ID)
        resource = request_body.get(const.ARG_RESOURCE)
        Log.debug(f"Get Capcity usage of resource: {resource} by id = {resource_id}")

        #plugin_response =await self._s3_iam_plugin.execute(const.GET_CAPACITY_USAGE_OPERATION, **request_body)
        plugin_response = {}
        if isinstance(plugin_response, RgwError):
            self._handle_error(plugin_response)

        return await self.create_response_body(resource, plugin_response)
