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


class ClusterOperationsAppService(ApplicationService):
    """
    Operations on cluster.
    """

    def __init__(self, plugin):
        self._cluster_operations_plugin = plugin

    async def request_operation(self, resource, resource_id, operation, **filters):
        """
        Operations on cluster.
        """
        plugin_request_params = self._build_request_parameters(resource, resource_id, operation, filters)
        Log.debug(f"Cluster operation {operation} on {resource} with filters: \
                    {plugin_request_params}")

        plugin_response = self._cluster_operations_plugin.process_request(**plugin_request_params)
        return plugin_response

    def _build_request_parameters(self, resource, resource_id, operation, filters):
        """
        Build request parameters based on the filters.
        """
        request_params = dict()
        request_params[const.PLUGIN_REQUEST] = const.PROCESS_CLUSTER_OPERATION_REQ
        request_params[const.ARG_RESOURCE] = resource
        request_params[const.ARG_RESOURCE_ID] = resource_id
        request_params[const.ARG_OPERATION] = operation
        request_params[const.ARG_FORCE] = filters.get(const.ARG_FORCE, False)

        return request_params
