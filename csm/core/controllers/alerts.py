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
from aiohttp import web
from marshmallow import Schema, fields, validate, ValidationError, validates
from csm.core.services.alerts import AlertsAppService
from csm.common.errors import InvalidRequest

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
    show_all = fields.Boolean(default=True, missing=True, allow_none=True)
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

# TODO: Implement base class for sharing common controller logic
class AlertsListView(web.View):
    def __init__(self, request, alerts_service: AlertsAppService):
        super().__init__(request)
        self.alerts_service = alerts_service

    async def get(self):
        """Calling Alerts Get Method"""
        alerts_qp = AlertsQueryParameter()
        try:
            alert_data = alerts_qp.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid Parameter for alerts", str(val_err))

        return await self.alerts_service.fetch_all_alerts(**alert_data)


class AlertsView(web.View):
    def __init__(self, request, alerts_service: AlertsAppService):
        super().__init__(request)
        self.alerts_service = alerts_service

    async def patch(self):
        """ Update Alert """
        alert_id = self.request.match_info["alert_id"]
        try:
            body = await self.request.json()
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        return await self.alerts_service.update_alert(alert_id, body)


# AIOHTTP does not provide a way to pass custom parameters to its views.
# It is a workaround.
class AlertsHttpController:
    def __init__(self, alerts_service: AlertsAppService):
        self.alerts_service = alerts_service

    def get_list_view_class(self):
        class Child(AlertsListView):
            def __init__(child_self, request):
                super().__init__(request, self.alerts_service)
        return Child

    def get_view_class(self):
        class Child(AlertsView):
            def __init__(child_self, request):
                super().__init__(request, self.alerts_service)
        return Child
