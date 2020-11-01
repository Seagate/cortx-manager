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
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.core.controllers.validators import Enum, ValidationErrorFormatter, Server, PortValidator
from marshmallow import (Schema, fields, ValidationError)
from csm.common.permission_names import Resource, Action


class GetPreFlightSchema(Schema):
    db_name = fields.Str(required=True, validate=[Enum([const.PREFLIGHT_CONSUL, const.PREFLIGHT_ELASTICSEARCH])])


@CsmView._app_routes.view("/api/v1/pre_flight")
@CsmAuth.public
class PreflightAllView(CsmView):
    def __init__(self, request):
        super(PreflightAllView, self).__init__(request)
        self._service = self.request.app[const.PREFLIGHT_SERVICE]

    async def get(self):
        """
        Fetch All pre flight status.
        """
        Log.debug("Handling all pre flight request")
        resp =  await self._service.check_status([const.PREFLIGHT_CONSUL, const.PREFLIGHT_ELASTICSEARCH])
        if not resp['success']:
            return CsmResponse(resp, status=503)
        return resp

@CsmView._app_routes.view("/api/v1/pre_flight/{db_name}")
@CsmAuth.public
class PreflightView(CsmView):
    def __init__(self, request):
        super(PreflightView, self).__init__(request)
        self._service = self.request.app[const.PREFLIGHT_SERVICE]

    async def get(self):
        """
        Fetch All pre flight status.
        """
        Log.debug("Handling pre flight request")
        # action = self.request.match_info[const.PREFLIGHT_CONSUL]
        try:
            db_name = GetPreFlightSchema().load(self.request.match_info,
                                        unknown=const.MARSHMALLOW_EXCLUDE)
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        resp =  await self._service.check_status([db_name['db_name']])
        if not resp['success']:
            return CsmResponse(resp, status=503)
        return resp
