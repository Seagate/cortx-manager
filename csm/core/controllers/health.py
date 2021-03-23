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
from csm.core.controllers.view import CsmView
from marshmallow import Schema, fields, validate, ValidationError, validates
from csm.core.controllers.validators import ValidationErrorFormatter, Enum
from csm.common.errors import InvalidRequest
from cortx.utils.log import Log
from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.blogic import const

class HealthViewQueryParameter(Schema):
    node_id = fields.Str(default=None, missing=None)

class HealthResourceViewQueryParameter(Schema):
    severity_values = [const.OK, const.CRITICAL, const.WARNING]
    component_id = fields.Str(default=None, missing=None)
    severity = fields.Str(default=const.OK, missing=const.OK, validate=[Enum(severity_values)])

@CsmView._app_routes.view("/api/v1/system/health/summary")
@CsmView._app_routes.view("/api/v2/system/health/summary")
class HealthSummaryView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        return await self.health_service.fetch_health_summary()

@CsmView._app_routes.view("/api/v1/system/health/view")
@CsmView._app_routes.view("/api/v2/system/health/view")
class HealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """
        Calling Health Get Method
        """
        Log.debug(f"Fetch Health view. "
                  f"user_id: {self.request.session.credentials.user_id}")
        health_view_qp = HealthViewQueryParameter()
        try:
            health_view_data = health_view_qp.load(self.request.rel_url.query,
                                        unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        node_health_summary = await self.health_service.fetch_health_view(**health_view_data)
        return node_health_summary

@CsmView._app_routes.view("/api/v1/system/health/components")
@CsmView._app_routes.view("/api/v2/system/health/components")
class HealthComponentView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """
        Calling Health Get Method
        """
        Log.debug(f"Fetch Health view. "
                  f"user_id: {self.request.session.credentials.user_id}")
        health_view_qp = HealthViewQueryParameter()
        try:
            health_view_data = health_view_qp.load(self.request.rel_url.query,
                                        unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        component_health_summary = await self.health_service.fetch_component_health_view(**health_view_data)
        return component_health_summary

@CsmView._app_routes.view("/api/v1/system/health/node")
@CsmView._app_routes.view("/api/v2/system/health/node")
class NodeHealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """
        Calling Health Get Method
        """
        Log.debug(f"Fetch Health view. "
                  f"user_id: {self.request.session.credentials.user_id}")
        health_view_qp = HealthViewQueryParameter()
        try:
            health_view_data = health_view_qp.load(self.request.rel_url.query,
                                        unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        node_health_summary = await self.health_service.fetch_node_health(**health_view_data) 
        return node_health_summary

@CsmView._app_routes.view("/api/v1/system/health/resources")
@CsmView._app_routes.view("/api/v2/system/health/resources")
class HealthResourceView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.HEALTH: {Action.LIST}})
    async def get(self):
        """
        Calling Get Method to show resources based on severity
        """
        Log.debug(f"Fetching health based on severity. "
                  f"user_id: {self.request.session.credentials.user_id}")
        try:
            health_view_qp = HealthResourceViewQueryParameter()
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        try:
            health_view_data = health_view_qp.load(self.request.rel_url.query,
                                        unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        resource_health = await self.health_service.get_resources(**health_view_data)
        return resource_health
