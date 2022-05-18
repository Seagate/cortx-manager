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
from csm.common.plugin import CsmPlugin
from csm.common.errors import InvalidRequest
from csm.core.blogic import const


class HealthPlugin(CsmPlugin):
    """
    Communicates with HA via ha_framework to fetch health
    of resources based on filters.
    """

    def __init__(self, ha):
        super().__init__()

        self._ha = ha

    def init(self, **kwargs):
        pass

    def process_request(self, **kwargs):
        request = kwargs.get(const.PLUGIN_REQUEST, "")
        response = None

        Log.debug(f"Health plugin process_request with arguments: {kwargs}")
        if request == const.FETCH_RESOURCE_HEALTH_REQ:
            response = self._fetch_resource_health(kwargs)

        return response

    def _fetch_resource_health(self, filters):
        """
        Make call to CortxHAFramework get_system_health method
        to get the health of resources.
        """
        resource = filters.get(const.ARG_RESOURCE, "")
        depth = filters.get(const.ARG_DEPTH, const.HEALTH_DEFAULT_DEPTH)
        args = HealthPlugin._build_args_to_get_system_health(filters)

        response_format = filters.get(const.ARG_RESPONSE_FORMAT,
                                        const.RESPONSE_FORMAT_TREE)

        if response_format == const.RESPONSE_FORMAT_TABLE:
            depth = 0

        resource_health = self._ha.get_system_health(resource, depth, **args)
        resource_health_resp = self._parse_ha_resp(resource_health, filters)

        return resource_health_resp

    @staticmethod
    def _build_args_to_get_system_health(filters):
        args = dict()

        resource_id = filters.get(const.ARG_RESOURCE_ID, "")
        if resource_id != "":
            args["id"] = resource_id

        return args

    def _parse_ha_resp(self, resource_health, filters):
        resource_health_resp = dict()
        response_format = filters.get(const.ARG_RESPONSE_FORMAT,
                                    const.RESPONSE_FORMAT_TREE)

        if response_format == const.RESPONSE_FORMAT_TABLE:
            flattened_health_resp = self._flatten_ha_resp(resource_health)
            offset = filters.get(const.ARG_OFFSET, const.HEALTH_DEFAULT_OFFSET)
            limit = filters.get(const.ARG_LIMIT, const.HEALTH_DEFAULT_LIMIT)
            total_resources = len(flattened_health_resp)

            if limit == 0:
                limit = total_resources

            start = (offset - 1) * limit
            end = min((start + limit), total_resources)

            if start >= end:
                raise InvalidRequest(f"Invalid offset {offset}."
                                        " Offset is out of bounds.")

            resource_health_resp = {
                "data": flattened_health_resp[start:end],
                "total_records": total_resources
            }
        else:
            resource_health_resp["data"] = resource_health["health"]

        resource_health_resp["version"] = resource_health["version"]
        return resource_health_resp

    def _flatten_ha_resp(self, resource_health):
        resources = []
        stack = list()
        for res_health in reversed(resource_health.get("health", [])):
            stack.append(res_health)

        while len(stack) > 0:
            resource = stack.pop()
            resources.append(self._build_resource_obj(resource))

            if resource["sub_resources"] != None and len(resource["sub_resources"]) > 0:
                for sub_resource in reversed(resource["sub_resources"]):
                    stack.append(sub_resource)

        return resources

    @staticmethod
    def _build_resource_obj(resource):
        return {
            "resource" : resource["resource"],
            "id" : resource["id"],
            "status" : resource["status"],
            "last_updated_time" : resource["last_updated_time"]
        }
