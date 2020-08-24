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

from .view import CsmView, CsmAuth
from eos.utils.log import Log
from csm.core.blogic import const
from csm.common.permission_names import Resource, Action


@CsmView._app_routes.view("/api/v1/capacity")
class StorageCapacityView(CsmView):
    """
    GET REST API view implementation for getting disk capacity details.
    """
    def __init__(self, request):
        super(StorageCapacityView, self).__init__(request)
        self._service = self.request.app[const.STORAGE_CAPACITY_SERVICE]

    @CsmAuth.permissions({Resource.STATS: {Action.LIST}})
    @Log.trace_method(Log.DEBUG)
    async def get(self):
        return await self._service.get_capacity_details(format='human')


