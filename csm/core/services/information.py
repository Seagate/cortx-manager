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
from csm.common.errors import CsmUnauthorizedError

class InformationService(ApplicationService):
    """Version Comptibility Validation service class."""

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
    async def get_cortx_information(self, authorized=True):
        """
        Method to fetch the cortx information
        :param **request_body: Request body kwargs
        """
        #TODO: call utils api to get all information
        response = {}
        return response

    @Log.trace_method(Log.DEBUG)
    async def query_cortx_topology(self, authorized=True, **path_param):
        """
        Method to fetch the cortx topology
        :param **request_body: Request body kwargs
        """
        Log.debug(f"Request body: {resource}")
        resource = path_param[const.ARG_RESOURCE]
        resource_id = path_param[const.ARG_RESOURCE_ID]
        view = path_param[const.ARG_VIEW]
        view_id = path_param[const.ARG_VIEW_ID]
        #if not authorized and resource == "certificate":
        #    raise CsmUnauthorizedError("Invalid authentication credentials for the target resource.")
        # TODO: Call Utils API to get information
        # TODO: Adding mapping
        # Sample Response
        response = {
            "cluster" : {
                "info": {
                    "CORTX": "2.0.0-123"
                }
            },
            "certificate" : {
                "info": {
                    "key": "value"
                }
            }
        }
        # Filter the Response based on authorization and resource
        #if authorized and resource is not None:
        #    return response.get(resource, None)
        #if not authorized:
        #    response.pop('certificate', None)
        return response
