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

from marshmallow import Schema, fields, validate, ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.validators import ValidationErrorFormatter, Enum


class HealthViewQueryParameter(Schema):
    response_format_values = [const.RESPONSE_FORMAT_TABLE, const.RESPONSE_FORMAT_TREE]
    resource_id = fields.Str(default="", missing="")
    depth = fields.Int(validate=validate.Range(min=0),
                       default=const.HEALTH_DEFAULT_DEPTH,
                       missing=const.HEALTH_DEFAULT_DEPTH)
    response_format = fields.Str(default=const.RESPONSE_FORMAT_TREE,
                                 missing=const.RESPONSE_FORMAT_TREE,
                                 validate=[Enum(response_format_values)])
    offset = fields.Int(validate=validate.Range(min=1),
                        allow_none=True,
                        default=const.HEALTH_DEFAULT_OFFSET,
                        missing=const.HEALTH_DEFAULT_OFFSET)
    limit = fields.Int(validate=validate.Range(min=0),
                       allow_none=True,
                       default=const.HEALTH_DEFAULT_LIMIT,
                       missing=const.HEALTH_DEFAULT_LIMIT)


@CsmView._app_routes.view("/api/v2/system/health/{resource}")
class ResourcesHealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """Get health of all resources of type {resource} and/or their sub resources."""
        resource = self.request.match_info["resource"]
        health_view_qp_obj = HealthViewQueryParameter()
        try:
            health_view_qp = health_view_qp_obj.load(self.request.rel_url.query,
                                                     unknown='EXCLUDE')
            Log.debug(f"Fetch Health of {resource} "
                      f"with query parameters {health_view_qp}."
                      f"user_id: {self.request.session.credentials.user_id}")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        resources_health = await self.health_service.fetch_resources_health(
            resource, **health_view_qp)
        return resources_health
