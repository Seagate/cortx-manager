#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          health.py
 Description:       Controllers for health

 Creation Date:     02/18/2020
 Author:            Soniya Moholkar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import re
from aiohttp import web
from csm.core.controllers.view import CsmView
from marshmallow import Schema, fields, validate, ValidationError, validates
from csm.core.controllers.validators import ValidationErrorFormatter
from csm.common.errors import InvalidRequest
from eos.utils.log import Log
from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.blogic import const

class HealthViewQueryParameter(Schema):
    node_id = fields.Str(default=None, missing=None)

@CsmView._app_routes.view("/api/v1/system/health/summary")
class HealthSummaryView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    async def get(self):
        return await self.health_service.fetch_health_summary()

@CsmView._app_routes.view("/api/v1/system/health/view")
class HealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]
        
    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    async def get(self):
        """Calling Alerts Get Method"""
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

@CsmView._app_routes.view("/api/v1/system/health/node")
class NodeHealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app[const.HEALTH_SERVICE]

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}}) 
    async def get(self):
        """Calling Alerts Get Method"""
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
