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
from csm.core.blogic import const


class HealthPlugin(CsmPlugin):
    """
    """

    def __init__(self, ha):
        super().__init__()
        try:
            self._ha = ha
        except Exception as e:
            Log.exception(e)

    def init(self, **kwargs):
        pass

    def process_request(self, **kwargs):
        request = kwargs.get(const.PLUGIN_REQUEST, "")
        response = None
        if request == const.FETCH_RESOURCE_HEALTH_REQ:
            response = self._fetch_resource_health(kwargs)

        return response

    def _fetch_resource_health(self, filters):
        resource = filters.get(const.ARG_RESOURCE, "")
        resource_id = filters.get(const.ARG_RESOURCE_ID, "")
        depth = filters.get(const.ARG_DEPTH, 1)

        resource_health = self._ha.get_system_health(resource, depth, id=resource_id)
        resource_health_resp = self._parse_ha_resp(resource_health, filters)
        
        return resource_health_resp

    def _parse_ha_resp(self, resource_health, filters):
        resource_health_resp = dict()
        response_format = filters.get(const.ARG_RESPONSE_FORMAT,
                                    const.RESPONSE_FORMAT_TREE)

        if response_format == const.RESPONSE_FORMAT_TABLE:
            flattened_health_resp = self._flatten_ha_resp(resource_health)
            offset = filters.get(const.ARG_OFFSET, 1)
            limit = filters.get(const.ARG_LIMIT, 0)
            total_resources = len(flattened_health_resp)
            effective_limit = min(limit, total_resources)
            start = (offset - 1) * limit
            end = start + effective_limit
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

            if len(resource["sub_resources"]) > 0:
                for sub_resource in reversed(resource["sub_resources"]):
                    stack.append(sub_resource)

        return resources

    def _build_resource_obj(self, resource):
        return {
            "resource" : resource["resource"],
            "id" : resource["id"],
            "status" : resource["status"],
            "last_updated_time" : resource["last_updated_time"]
        }
