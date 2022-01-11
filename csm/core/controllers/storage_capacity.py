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
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.permission_names import Resource, Action
from csm.common.errors import InvalidRequest


@CsmView._app_routes.view("/api/v1/capacity")
@CsmView._app_routes.view("/api/v2/capacity")
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
        unit = self.request.query.get(const.UNIT,const.DEFAULT_CAPACITY_UNIT)
        round_off_value = int(self.request.query.get(const.ROUNDOFF_VALUE,const.DEFAULT_ROUNDOFF_VALUE))
        if round_off_value <= 0:
            raise InvalidRequest(f"Round off value should be greater than 0. Default value:{const.DEFAULT_ROUNDOFF_VALUE}")
        if (not unit.upper() in const.UNIT_LIST) and (not unit.upper()==const.DEFAULT_CAPACITY_UNIT):
            raise InvalidRequest(f"Invalid unit. Please enter units from {','.join(const.UNIT_LIST)}. Default unit is:{const.DEFAULT_CAPACITY_UNIT}")
        return await self._service.get_capacity_details(unit=unit, round_off_value=round_off_value)


@CsmAuth.hybrid
@CsmView._app_routes.view("/api/v2/cluster/status")
class CapacityManagementView(CsmView):
    """
    GET REST API view implementation for getting cluster status
    """
    def __init__(self, request):
        super(CapacityManagementView, self).__init__(request)
        self._service = self.request.app[const.STORAGE_CAPACITY_SERVICE]

    @CsmAuth.permissions({Resource.CAPACITY: {Action.LIST}})
    @Log.trace_method(Log.DEBUG)
    async def get(self):
        #TODO: Accept path parameter from URL to get filtered data as per paramter.
        # Integration ticket to be taken in Sprint-60.
        Log.info("Handling GET implementation for getting cluster staus data")
        return await self._service.get_cluster_data()
