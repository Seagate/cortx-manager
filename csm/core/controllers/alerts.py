#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          alerts.py
 Description:       Controllers for alerts

 Creation Date:     09/05/2019
 Author:            Alexander Nogikh

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
from csm.common.log import Log
from aiohttp import web
from marshmallow import Schema, fields, validate, ValidationError, validates
from csm.common.errors import InvalidRequest
from csm.core.controllers.view import CsmView
from csm.core.blogic import const
from csm.core.controllers.validators import ValidationErrorFormatter
from csm.common.log import Log

ALERTS_MSG_INVALID_DURATION = "alert_invalid_duration"
"""
this will go into models
"""


class AlertsQueryParameter(Schema):
    duration = fields.Str(default=None, missing=None)
    offset = fields.Int(validate=validate.Range(min=0), allow_none=True,
        default=0, missing=0)
    page_limit = fields.Int(data_key='limit', default=5, validate=validate.Range(min=0), missing=5)
    sort_by = fields.Str(data_key='sortby', default="created_time", missing="created_time")
    direction = fields.Str(data_key='dir', validate=validate.OneOf(['desc', 'asc']), 
        missing='desc', default='desc')
    show_all = fields.Boolean(default=False, missing=False, allow_none=True)
    severity = fields.Str(default=None, missing=None, allow_none=True)
    resolved = fields.Boolean(default=None, missing=None)
    acknowledged = fields.Boolean(default=None, missing=None)

    @validates('duration')
    def validate_duration(self, value):
        if value:
            time_duration = int(re.split(r'[a-z]', value)[0])
            time_format = re.split(r'[0-9]', value)[-1]
            dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            if time_format not in dur.keys():
                raise InvalidRequest(
                    "Invalid Parameter for Duration", ALERTS_MSG_INVALID_DURATION)

    class Meta:
        strict = False

@CsmView._app_routes.view("/api/v1/alerts")
# TODO: Implement base class for sharing common controller logic
class AlertsListView(web.View):
    def __init__(self, request):
        super().__init__(request)
        self.alerts_service = self.request.app["alerts_service"]

    async def get(self):
        """Calling Alerts Get Method"""
        Log.debug(f"Handling list alerts get request."
                  f"user_id: {self.request.session.credentials.user_id}")
        alerts_qp = AlertsQueryParameter()
        try:
            alert_data = alerts_qp.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid Parameter for alerts", str(val_err))
        return await self.alerts_service.fetch_all_alerts(**alert_data)

    async def patch(self):
        Log.debug(f"Handling update all alerts patch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            body = await self.request.json()
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")

        return await self.alerts_service.update_all_alerts(body)


@CsmView._app_routes.view("/api/v1/alerts/{alert_id}")
class AlertsView(web.View):
    def __init__(self, request):
        super().__init__(request)
        self.alerts_service = self.request.app["alerts_service"]

    async def patch(self):        
        """ Update Alert """    
        alert_id = self.request.match_info["alert_id"]
        Log.debug(f"Handling update alerts patch request for id: {alert_id}."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            body = await self.request.json()
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        return await self.alerts_service.update_alert(alert_id, body)

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
class AlertCommentsView(web.View):
    def __init__(self, request):
        super().__init__(request)
        self.user_id = self.request.session.credentials.user_id
        self.alerts_service = self.request.app["alerts_service"]

    @Log.trace_method(Log.DEBUG)
    async def get(self):
        """ Get all the comments of alert having alert_uuid """
        alert_uuid = self.request.match_info["alert_uuid"]

        #  Fetching the alert to make sure that alert exists for the alert_uuid provided
        return await self.alerts_service.fetch_comments_for_alert(alert_uuid)

    @Log.trace_method(Log.DEBUG)
    async def post(self):
        """ Add Comment to Alert having alert_uuid """
        alert_uuid = self.request.match_info["alert_uuid"]

        try:
            schema = AlertCommentsCreateSchema()
            comment_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as ve:
            raise InvalidRequest(ValidationErrorFormatter.format(ve))

        return await self.alerts_service.add_comment_to_alert(alert_uuid, self.user_id, comment_body["comment_text"])
