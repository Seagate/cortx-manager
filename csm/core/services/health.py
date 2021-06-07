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

from csm.common.services import ApplicationService
from csm.core.blogic import const
from cortx.utils.log import Log


class HealthAppService(ApplicationService):
    """
    Provides operations to fetch health of resources
    from HA.
    """

    def __init__(self, plugin):
        self._health_plugin = plugin

    async def fetch_resources_health(self, resource, **filters):
        """
        Fetch health of all resources of type {resource}
        and/or their sub resources based on input level.
        """
        plugin_request_params = self._build_request_parameters(filters)
        plugin_request_params[const.ARG_RESOURCE] = resource

        plugin_response = self._health_plugin.process_request(**plugin_request_params)
        return plugin_response

    async def fetch_resource_health_by_id(self, resource, resource_id, **filters):
        """
        Get health of resource (cluster, site, rack, node etc.)
        with resource_id and/or its sub resources based on input level.
        """
        plugin_request_params = self._build_request_parameters(filters)
        plugin_request_params[const.ARG_RESOURCE] = resource
        plugin_request_params[const.ARG_RESOURCE_ID] = resource_id

        plugin_response = self._health_plugin.process_request(**plugin_request_params)
        return plugin_response

    def _build_request_parameters(self, filters):
        request_params = dict()
        request_params[const.PLUGIN_REQUEST] = const.FETCH_RESOURCE_HEALTH_REQ
        request_params[const.ARG_DEPTH] = filters.get(const.ARG_DEPTH, 1)
        request_params[const.ARG_OFFSET] = filters.get(const.ARG_OFFSET, 1)
        request_params[const.ARG_LIMIT] = filters.get(const.ARG_LIMIT, 0)
        request_params[const.ARG_RESPONSE_FORMAT] = filters.get(
                                                        const.ARG_RESPONSE_FORMAT,
                                                        const.RESPONSE_FORMAT_TREE)

        return request_params

