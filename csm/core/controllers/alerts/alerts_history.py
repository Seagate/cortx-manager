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

import re
from cortx.utils.log import Log
from aiohttp import web
from typing import Dict
from marshmallow import Schema, fields, validate, ValidationError, validates, \
        validates_schema
from csm.common.errors import InvalidRequest
from csm.core.controllers.view import CsmView, CsmAuth
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.validators import ValidationErrorFormatter
from datetime import date, datetime

ALERTS_MSG_INVALID_DURATION = "alert_invalid_duration"

class AlertsHistoryQueryParameter(Schema):
    duration = fields.Str(default=None, missing=None)
    offset = fields.Int(validate=validate.Range(min=0), allow_none=True,
        default=0, missing=0)
    """
    Setting the limit to 1000 to limit the alerts records.
    """
    page_limit = fields.Int(data_key='limit', default=1000, \
            validate=validate.Range(min=0), missing=1000)
    sort_by = fields.Str(data_key='sortby', default="created_time", missing="created_time")
    direction = fields.Str(data_key='dir', validate=validate.OneOf(['desc', 'asc']), 
        missing='desc', default='desc')
    sensor_info = fields.Str(default=None, missing=None, allow_none=True)
    start_date = fields.Str(data_key='start_date', default=None, missing=None, \
            allow_none=True)
    end_date = fields.Str(data_key='end_date', default=None, missing=None, \
            allow_none=True)

    @validates('duration')
    def validate_duration(self, value):
        if value:
            time_duration = int(re.split(r'[a-z]', value)[0])
            time_format = re.split(r'[0-9]', value)[-1]
            dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            if time_format not in dur.keys():
                raise InvalidRequest(
                    "Invalid Parameter for Duration", ALERTS_MSG_INVALID_DURATION)

    @validates_schema
    def check_date(self, data: Dict, *args, **kwargs):
        if data["start_date"]:
            if not data["end_date"]:
                """
                If end_date not provided we will use the current date.
                """
                data["end_date"] = date.today()
            else:
                data["end_date"] = datetime.strptime(data["end_date"],\
                        '%Y-%m-%d').date()

            data["start_date"] = datetime.strptime(data["start_date"],
                    '%Y-%m-%d').date()
            if data["start_date"] > data["end_date"]:
                raise ValidationError(
                    "start date cannot be greater than end date.",
                    field_name="start_date")
            elif data["start_date"] > date.today() or data["end_date"] > date.today():
                raise ValidationError(
                    "Start/End date cannot be greater than today.")

    class Meta:
        strict = False

@CsmView._app_routes.view("/api/v1/alerts_history")
@CsmView._app_routes.view("/api/v2/alerts_history")
class AlertsHistoryListView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.alerts_service = self.request.app["alerts_service"]

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    async def get(self):
        """Calling Alerts Get Method"""
        Log.debug(f"Handling get request for listing of alerts history."
                  f"user_id: {self.request.session.credentials.user_id}")
        alerts_history_qp = AlertsHistoryQueryParameter()
        try:
            alerts_history_data = alerts_history_qp.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        return await self.alerts_service.fetch_all_alerts_history(**alerts_history_data)

@CsmView._app_routes.view("/api/v1/alerts_history/{alert_id}")
@CsmView._app_routes.view("/api/v2/alerts_history/{alert_id}")
class AlertsHistoryView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.alerts_service = self.request.app["alerts_service"]

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    async def get(self):
        """ Gets alert by ID """
        Log.debug(f"Handling fetching of alerts history: get request by alert id."
                  f"user_id: {self.request.session.credentials.user_id}")
        alert_id = self.request.match_info["alert_id"]
        return await self.alerts_service.fetch_alert_history(alert_id)
