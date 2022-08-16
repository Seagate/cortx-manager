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
from csm.core.blogic import const
from csm.common.services import ApplicationService
from cortx.utils.schema.release import Release
from csm.common.errors import CsmInternalError, CsmNotFoundError

class InformationService(ApplicationService):
    """Version Comptibility Validation service class."""

    def __init__(self, plugin):
        self._plugin = plugin

    @Log.trace_method(Log.DEBUG)
    async def check_compatibility(self, **request_body):
        """
        Method to check whether new version are compatible with deployed version

        :param **request_body: Request body kwargs
        """
        Log.debug(f"Request body: {request_body}")
        # Invoke api to check compatibility
        resource = request_body[const.ARG_RESOURCE]
        resource_id = request_body[const.ARG_RESOURCE_ID]
        release = request_body[const.REQUIRES]
        status, reason = Release.is_version_compatible(resource, resource_id, release)

        # handle the response and return
        response = {
            "node_id": request_body.get(const.ARG_RESOURCE_ID),
            "compatible": status,
            "reason": reason
        }
        return response

    @Log.trace_method(Log.DEBUG)
    async def get_topology(self):
        """
        Get topology
        """
        try:
            plugin_response = self._plugin.get_topology()
        except CsmInternalError as e:
            raise e
        return plugin_response

    @Log.trace_method(Log.DEBUG)
    async def get_resources(self, resource):
        """
        Fetch all resources from topology
        """
        try:
            plugin_response = self._plugin.get_topology()
        except CsmInternalError as e:
            raise e
        payload  = plugin_response[const.TOPOLOGY]
        if isinstance(plugin_response[const.TOPOLOGY], dict):
            plugin_response[const.TOPOLOGY] = {key:value for key, value in \
                payload.items() if key == resource}
        return plugin_response

    @Log.trace_method(Log.DEBUG)
    async def get_specific_resource(self, resource, resource_id):
        """
        Fetch specific resource from topology
        """
        response = await self.get_resources(resource)
        payload = response[const.TOPOLOGY][resource]
        if isinstance(payload, list):
            response[const.TOPOLOGY][resource] = [item for item in \
                payload if item.get(const.ID) == resource_id]
            if len(response[const.TOPOLOGY][resource]) < 1:
                raise CsmNotFoundError(f"Invalid resource_id: {resource_id}")
        return response

    @Log.trace_method(Log.DEBUG)
    async def get_views(self, resource, resource_id, view):
        """
        Fetch all view of specific resource topology
        """

        res = await self.get_specific_resource(resource, resource_id)
        payload = res[const.TOPOLOGY][resource][0]
        if isinstance(payload, dict):
            response = {
                const.ID: payload[const.ID],
                view: payload[view]
            }
            res[const.TOPOLOGY][resource][0] = response
        return res

    @Log.trace_method(Log.DEBUG)
    async def get_specific_view(self, **path_param):
        """
        Fetch specific view of specific resource from topology
        """
        resource = path_param[const.ARG_RESOURCE]
        resource_id = path_param[const.ARG_RESOURCE_ID]
        view = path_param[const.ARG_VIEW]
        view_id = path_param[const.ARG_VIEW_ID]
        res = await self.get_views(resource, resource_id, view)
        payload = res[const.TOPOLOGY][resource][0][view]
        if isinstance(payload, list):
            res[const.TOPOLOGY][resource][0][view] = [item for item in \
                payload if item.get(const.ID) == view_id]
            if len(res[const.TOPOLOGY][resource][0][view]) < 1:
                raise CsmNotFoundError(f"Invalid resource_id: {view_id}")
        return res
