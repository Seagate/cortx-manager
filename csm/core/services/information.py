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

import resource
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.services import ApplicationService
from cortx.utils.schema.release import Release
from csm.common.errors import CsmUnauthorizedError

class InformationService(ApplicationService):
    """Version Comptibility Validation service class."""

    def __init__(self, plugin):
        self._query_deployment_plugin = plugin
        self.resource_id_key = {"cluster": "id"}

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

    def get_topology(self):
        """
        Method to fetch the cortx topology
        :param **request_body: Request body kwargs
        """
        plugin_response = self._query_deployment_plugin.get_topology()
        return plugin_response

    def _filter_from_dict(self, inputdict, keyword):
        res = inputdict.copy()
        for item in inputdict:
            if item != keyword:
                res.pop(item)
        return res

    def get_all_resources(self, resource):
        """
        Method to fetch the cortx topology
        :param **request_body: Request body kwargs
        """
        plugin_response = self._query_deployment_plugin.get_topology()
        # TODO: Add plugin response from plugin section
        plugin_response['topology'] = self._filter_from_dict(plugin_response['topology'])
        return plugin_response

    def get_resource(self, resource, resource_id):
        """
        Method to fetch the cortx topology
        :param **request_body: Request body kwargs
        """
        res = self.get_all_resources(resource)
        payload = res["topology"][resource]
        key = self.resource_id_key[resource]
        res["topology"][resource] = [item for item in payload if item.get(key) != resource]
        return res

    def get_all_views(self, resource, resource_id, view):
        """
        Method to fetch the cortx topology
        :param **request_body: Request body kwargs
        """
        #TODO: call plugin
        response = {}
        return response

    def get_view(self, **path_param):
        """
        Method to fetch the cortx topology
        :param **request_body: Request body kwargs
        """
        Log.debug(f"Request body: {resource}")
        resource = path_param[const.ARG_RESOURCE]
        resource_id = path_param[const.ARG_RESOURCE_ID]
        view = path_param[const.ARG_VIEW]
        view_id = path_param[const.ARG_VIEW_ID]
        #TODO: call plugin
        response = {}
        return response
