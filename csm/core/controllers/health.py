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

import json
import re
from aiohttp import web
from marshmallow import Schema, fields, validate, ValidationError, validates
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.validators import ValidationErrorFormatter, Enum


class HealthViewQueryParameter(Schema):
    response_format_values = [const.RESPONSE_FORMAT_TABLE, const.RESPONSE_FORMAT_TREE]
    depth = fields.Number(default=1, missing=1)
    response_format = fields.Str(default=const.RESPONSE_FORMAT_TREE, \
                                    missing=const.RESPONSE_FORMAT_TREE, \
                                    validate=[Enum(response_format_values)])


@CsmView._app_routes.view("/api/v2/system/health/{resource}")
class ResourcesHealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """
        Get health of all resources of type {resource} 
        and/or their sub resources based on input depth.
        """
        resource = self.request.match_info["resource"]
        Log.debug(f"Fetch Health of {resource}."
                  f"user_id: {self.request.session.credentials.user_id}")
        health_view_qp_obj = HealthViewQueryParameter()
        try:
            health_view_qp = health_view_qp_obj.load(self.request.rel_url.query,
                                        unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        resources_health = await self.health_service.fetch_resources_health(**health_view_qp)
        return resources_health


@CsmView._app_routes.view("/api/v2/system/health/{resource}/{resource_id}")
class ResourceHealthByIdView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """
        Get health of resource (cluster, site, rack, node etc.)
        with resource_id and/or its sub resources based on input level. 
        """
        resource = self.request.match_info["resource"]
        resource_id = self.request.match_info["resource_id"]
        Log.debug(f"Fetch Health of {resource} having id {resource_id}."
                  f"user_id: {self.request.session.credentials.user_id}")
        health_view_qp_obj = HealthViewQueryParameter()
        try:
            health_view_qp = health_view_qp_obj.load(self.request.rel_url.query,
                                        unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        resource_health = await self.health_service.fetch_resource_health_by_id(**health_view_qp)
        return resource_health
