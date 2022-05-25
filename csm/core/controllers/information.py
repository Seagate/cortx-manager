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

from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.errors import CsmNotFoundError

@CsmAuth.hybrid
@CsmView._app_routes.view("/api/v2/system/topology")
class CortxAboutInformationView(CsmView):
    """
    CORTX About information REST API implementation.

    GET: Cortx About information
    """
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.INFORMATION_SERVICE]

    async def get(self):
        """GET REST implementation for About Information."""
        Log.debug("Handling GET request for Cortx About information.")
        # Check if request is authenticated 
        is_authenticated = False
        if self.request.session is not None:
            is_authenticated = True
        # Call Cortx Information Service
        response = await self._service.get_cortx_information(is_authenticated)
        return CsmResponse(response)

@CsmAuth.hybrid
@CsmView._app_routes.view("/api/v2/system/topology/{resource}")
class ResourceAboutInformationView(CsmView):
    """
    CORTX About information REST API implementation.

    GET: Cortx About information
    """
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.INFORMATION_SERVICE]

    async def get(self):
        """GET REST implementation for About Information."""
        Log.debug("Handling GET request for Cortx About information.")
        # Read path parameter
        resource = self.request.match_info[const.ARG_RESOURCE]
        # Check for valid Resource
        if resource not in const.ABOUT_INFO_RESOURCES:
            raise CsmNotFoundError(f"{resource} is not valid")
        # Check if request is authenticated 
        is_authenticated = False
        if self.request.session is not None:
            is_authenticated = True
        # Call Cortx Information Service
        Log.debug(f"Fetching cortx information for {resource}.")
        response = await self._service.get_cortx_information(is_authenticated, resource)
        return CsmResponse(response)

