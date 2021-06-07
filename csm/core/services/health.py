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


class HealthAppService(ApplicationService):
    """
    Provides operations to fetch health of resources
    from HA.
    """

    def __init__(self, plugin):
        self._health_plugin = plugin

    async def fetch_resources_health(self, resource, **kwargs):
        """
        Fetch health of all resources of type {resource}
        and/or their sub resources based on input level.
        """
        depth = kwargs.get(const.ARG_DEPTH, 1)
        response_format = kwargs.get(const.ARG_RESPONSE_FORMAT, const.RESPONSE_FORMAT_TREE)

        return {'version': '1.0', 'data': []}

    async def fetch_resource_health_by_id(self, resource, resource_id, **kwargs):
        """
        Get health of resource (cluster, site, rack, node etc.)
        with resource_id and/or its sub resources based on input level.
        """
        depth = kwargs.get(const.ARG_DEPTH, 1)
        response_format = kwargs.get(const.ARG_RESPONSE_FORMAT, const.RESPONSE_FORMAT_TREE)

        return {'version': '1.0', 'data': []}
