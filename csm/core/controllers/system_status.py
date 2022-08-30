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

from .view import CsmView, CsmAuth, CsmResponse
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.core.blogic import const
from csm.core.controllers.validators import Enum, ValidationErrorFormatter
from marshmallow import (Schema, fields, ValidationError)


class GetSystemStatusSchema(Schema):
    db_name = fields.Str(required=True, validate=[Enum([const.CONSUL])])


@CsmView._app_routes.view("/api/v1/system/status")
@CsmView._app_routes.view("/api/v2/system/status")
@CsmAuth.public
class SystemStatusAllView(CsmView):
    def __init__(self, request):
        super(SystemStatusAllView, self).__init__(request)
        self._service = self.request.app[const.SYSTEM_STATUS_SERVICE]

    async def get(self):
        """Fetch All system status."""
        Log.debug("Handling all system status request")
        resp = await self._service.check_status([const.CONSUL])
        if not resp[const.SYSTEM_STATUS_SUCCESS]:
            return CsmResponse(resp, status=503)
        return resp


@CsmView._app_routes.view("/api/v1/system/status/{db_name}")
@CsmView._app_routes.view("/api/v2/system/status/{db_name}")
@CsmAuth.public
class SystemStatusView(CsmView):
    def __init__(self, request):
        super(SystemStatusView, self).__init__(request)
        self._service = self.request.app[const.SYSTEM_STATUS_SERVICE]

    async def get(self):
        """Fetch  system status."""
        Log.debug("Handling system status request")
        try:
            db_name = GetSystemStatusSchema().load(self.request.match_info,
                                                   unknown=const.MARSHMALLOW_EXCLUDE)
            Log.debug(f"Handling system status request for {db_name}")
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        resp = await self._service.check_status([db_name['db_name']])
        if not resp[const.SYSTEM_STATUS_SUCCESS]:
            return CsmResponse(resp, status=503)
        return resp
