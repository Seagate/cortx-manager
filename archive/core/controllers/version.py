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

from csm.core.controllers.view import CsmView, CsmAuth
from cortx.utils.log import Log
from csm.core.blogic import const

@CsmView._app_routes.view("/api/v1/product_version")
@CsmView._app_routes.view("/api/v2/product_version")
@CsmAuth.public
class ProductVersionView(CsmView):
    def __init__(self, request):
        super(ProductVersionView, self).__init__(request)
        self._service = self.request.app[const.PRODUCT_VERSION_SERVICE]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching product version details
    """
    async def get(self):
        Log.debug("Handling product version information fetch request")
        return await self._service.get_current_version()
    