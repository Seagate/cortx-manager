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
from csm.core.services.file_transfer import FileType
from cortx.utils.log import Log
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from marshmallow import Schema, fields, validate, ValidationError, validates
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action

class AuditLogRangeQuerySchema(Schema):
    """ schema to validate date range """
    start_date = fields.Int(required=True)
    end_date = fields.Int(required=True)

class AuditLogShowQuerySchema(AuditLogRangeQuerySchema):
    limit = fields.Int(validate=validate.Range(min=1))
    offset = fields.Int(validate=validate.Range(min=0))
    sort_by = fields.Str(data_key='sortby', missing="timestamp", default="timestamp")
    direction = fields.Str(data_key='dir', validate=validate.OneOf(['desc', 'asc']),
        missing='desc', default='desc')


@CsmView._app_routes.view("/api/v2/auditlogs/schema_info")
class AuditLogsSchemaInfo(CsmView):
    def __init__(self, request):
        super(AuditLogsSchemaInfo, self).__init__(request)
        self._service = self.request.app["audit_log"]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.AUDITLOG: {Action.LIST}})
    async def get(self):
        return await self._service.get_schema_info()


@CsmView._app_routes.view("/api/v1/auditlogs/show/{component}")
@CsmView._app_routes.view("/api/v2/auditlogs/show/{component}")
class AuditLogShowView(CsmView):
    def __init__(self, request):
        super(AuditLogShowView, self).__init__(request)
        self._service = self.request.app["audit_log"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching audit logs
    """
    @CsmAuth.permissions({Resource.AUDITLOG: {Action.LIST}})
    async def get(self):
        Log.debug("Handling audit log fetch request")
        component = self.request.match_info["component"]
        audit_log = AuditLogShowQuerySchema()
        try:
            request_data = audit_log.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid Range query", str(val_err))

        start_date = request_data["start_date"]
        end_date = request_data["end_date"] 
        limit = request_data.get('limit')
        offset = request_data.get('offset')
        sort_by = request_data.get('sort_by')
        direction = request_data.get('direction')
        return await self._service.get_by_range(
            component, start_date, end_date, limit=limit, offset=offset, sort_by=sort_by, direction=direction )

@CsmView._app_routes.view("/api/v1/auditlogs/download/{component}")
@CsmView._app_routes.view("/api/v2/auditlogs/download/{component}")
class AuditLogDownloadView(CsmView):
    def __init__(self, request):
        super(AuditLogDownloadView, self).__init__(request)
        self._service = self.request.app["audit_log"]
        self._file_service = self.request.app["download_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching audit logs
    """
    #Action.READ permission is used for downloading audit logs
    @CsmAuth.permissions({Resource.AUDITLOG: {Action.READ}})
    async def get(self):
        Log.debug("Handling audit log fetch request")
        component = self.request.match_info["component"]
        audit_log = AuditLogRangeQuerySchema()
        try:
            request_data = audit_log.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid Range query", str(val_err))

        start_date = request_data["start_date"]
        end_date = request_data["end_date"]
        zip_file = await self._service.get_audit_log_zip(component, start_date, end_date)
        return self._file_service.get_file_response(FileType.AUDIT_LOG, zip_file)

