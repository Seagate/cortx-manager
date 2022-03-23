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
from cortx.utils.log import Log
from aiohttp import web
from marshmallow import Schema, fields, validate, ValidationError, validates
from csm.core.services.alerts import AlertsAppService
from csm.common.errors import InvalidRequest
from csm.core.controllers.validators import CommentsValidator
from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.blogic import const
from csm.core.controllers.validators import ValidationErrorFormatter
from cortx.utils.log import Log
from csm.core.controllers.view import CsmView

ALERTS_MSG_INVALID_DURATION = "alert_invalid_duration"
INVALID_JSON_OR_BODY_MISSING = "Request body missing or invalid json"

"""
this will go into models
"""


class AlertsQueryParameter(Schema):
    duration = fields.Str(default=None, missing=None)
    offset = fields.Int(validate=validate.Range(min=0), allow_none=True,
        default=0, missing=0)
    page_limit = fields.Int(data_key='limit', default=1000, \
            validate=validate.Range(min=0), missing=1000)
    sort_by = fields.Str(data_key='sortby', default="created_time", missing="created_time")
    direction = fields.Str(data_key='dir', validate=validate.OneOf(['desc', 'asc']), 
        missing='desc', default='desc')
    show_all = fields.Boolean(default=False, missing=False, allow_none=True)
    severity = fields.Str(default=None, missing=None, allow_none=True)
    resolved = fields.Boolean(default=None, missing=None)
    acknowledged = fields.Boolean(default=None, missing=None)
    show_active = fields.Boolean(default=False, missing=False, allow_none=True)

    @validates('duration')
    def validate_duration(self, value):
        if value:
            time_duration = int(re.split(r'[a-z]', value)[0])
            time_format = re.split(r'[0-9]', value)[-1]
            dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            if time_format not in dur.keys():
                raise InvalidRequest(
                    "Invalid value for duration", ALERTS_MSG_INVALID_DURATION)

    class Meta:
        strict = False

class AlertsPatchParameter(Schema):
    acknowledged = fields.Boolean(required=False, default=None, missing=None)

    class Meta:
        strict = False
    
@CsmView._app_routes.view("/api/v1/alerts")
@CsmView._app_routes.view("/api/v2/alerts")
# TODO: Implement base class for sharing common controller logic
class AlertsListView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.alerts_service = self.request.app["alerts_service"]

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    @CsmView.asyncio_shield
    async def get(self):
        """Calling Alerts Get Method"""
        Log.debug(f"Handling list alerts get request."
                  f"user_id: {self.request.session.credentials.user_id}")
        alerts_qp = AlertsQueryParameter()
        try:
            alert_data = alerts_qp.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        return await self.alerts_service.fetch_all_alerts(**alert_data)

    @CsmAuth.permissions({Resource.ALERTS: {Action.UPDATE}})
    async def patch(self):
        Log.debug(f"Handling update all alerts patch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            body = await self.request.json()
        except json.decoder.JSONDecodeError:
            raise InvalidRequest("Request body missing or invalid json")
        return await self.alerts_service.update_all_alerts(body)


@CsmView._app_routes.view("/api/v1/alerts/{alert_id}")
@CsmView._app_routes.view("/api/v2/alerts/{alert_id}")
class AlertsView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.alerts_service = self.request.app["alerts_service"]

    @CsmAuth.permissions({Resource.ALERTS: {Action.UPDATE}})
    async def patch(self):        
        """ Update Alert """    
        alert_id = self.request.match_info["alert_id"]
        Log.debug(f"Handling update alerts patch request for id: {alert_id}."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            body_json = await self.request.json()
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(INVALID_JSON_OR_BODY_MISSING)
        
        alerts_body = AlertsPatchParameter()
        
        try:
            body = alerts_body.load(body_json, partial=True, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest("Invalid parameter for alerts", str(val_err))
        
        if not body:
            raise InvalidRequest("Invalid Parameter for alerts", message_args=body_json)
        return await self.alerts_service.update_alert(alert_id, body)

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    async def get(self):
        """ Gets alert by ID """
        alert_id = self.request.match_info["alert_id"]
        return await self.alerts_service.fetch_alert(alert_id)


class AlertCommentsCreateSchema(Schema):
    """
    Alert comment create schema
    """
    comment_text = fields.Str(required=True, validate=[validate.Length(min=1, max=const.STRING_MAX_VALUE)])


@CsmView._app_routes.view("/api/v1/alerts/{alert_uuid}/comments")
@CsmView._app_routes.view("/api/v2/alerts/{alert_uuid}/comments")
class AlertCommentsView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.user_id = self.request.session.credentials.user_id
        self.alerts_service = self.request.app["alerts_service"]

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    @Log.trace_method(Log.DEBUG)
    async def get(self):
        """ Get all the comments of alert having alert_uuid """
        alert_uuid = self.request.match_info["alert_uuid"]

        #  Fetching the alert to make sure that alert exists for the alert_uuid provided
        return await self.alerts_service.fetch_comments_for_alert(alert_uuid)

    @CsmAuth.permissions({Resource.ALERTS: {Action.UPDATE}})
    @Log.trace_method(Log.DEBUG)
    async def post(self):
        """ Add Comment to Alert having alert_uuid """
        alert_uuid = self.request.match_info["alert_uuid"]

        try:
            schema = AlertCommentsCreateSchema()
            comment_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(INVALID_JSON_OR_BODY_MISSING)
        except ValidationError as ve:
            raise InvalidRequest(ValidationErrorFormatter.format(ve))

        return await self.alerts_service.add_comment_to_alert(alert_uuid, self.user_id, comment_body["comment_text"])
