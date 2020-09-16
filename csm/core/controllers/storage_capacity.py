#!/usr/bin/env python3
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

from csm.common.errors import InvalidRequest
from csm.common.permission_names import Action, Resource
from csm.core.blogic import const
from .view import CsmAuth, CsmView


@CsmView._app_routes.view("/api/v1/capacity")
class StorageCapacityView(CsmView):
    """GET REST API view implementation for getting disk capacity details."""
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.STORAGE_CAPACITY_SERVICE]

    @CsmAuth.permissions({Resource.STATS: {Action.LIST}})
    @Log.trace_method(Log.DEBUG)
    async def get(self):
        unit = self.request.query.get(const.UNIT, const.DEFAULT_CAPACITY_UNIT)
        round_off_value = int(self.request.query.get(
            const.ROUNDOFF_VALUE, const.DEFAULT_ROUNDOFF_VALUE))
        if round_off_value <= 0:
            raise InvalidRequest("Round off value should be greater that 0. "
                                 f"Default value:{const.DEFAULT_ROUNDOFF_VALUE}")
        if ((not unit.upper() in const.UNIT_LIST)
                and (not unit.upper() == const.DEFAULT_CAPACITY_UNIT)):
            raise InvalidRequest(
                f"Invalid unit. Please enter units from {','.join(const.UNIT_LIST)}. "
                f"Default unit is:{const.DEFAULT_CAPACITY_UNIT}")
        return await self._service.get_capacity_details(unit=unit, round_off_value=round_off_value)
