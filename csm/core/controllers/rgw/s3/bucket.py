# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
from marshmallow import fields, ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth, CsmResponse
from csm.core.controllers.validators import ValidationErrorFormatter
from csm.core.controllers.rgw.s3.base import S3BaseView, S3BaseSchema

class LinkBucketSchema(S3BaseSchema):

    """
    S3 Bucket Link schema validation class.
    """
    uid = fields.Str(data_key=const.RGW_JSON_UID, required=True)
    bucket = fields.Str(data_key=const.RGW_JSON_BUCKET, required=True)
    bucket_id = fields.Str(data_key=const.RGW_JSON_BUCKET_ID, missing=None)

class UnlinkBucketSchema(S3BaseSchema):

    """
    S3 Bucket Unlink schema validation class.
    """
    uid = fields.Str(data_key=const.RGW_JSON_UID, required=True)
    bucket = fields.Str(data_key=const.RGW_JSON_BUCKET, required=True)

class schemaFactory:
    operation_schema_map = {
        "link": LinkBucketSchema,
        "unlink": UnlinkBucketSchema
    }
    @staticmethod
    def init(operation):
        return operation_schema_map[operation]()

@CsmView._app_routes.view("/api/v2/s3/bucket")
class S3BucketView(S3BaseView):

    """
    S3 Bucket View for REST API implementation.
    PUT: Bucket Opertation
    """

    def __init__(self, request):
        """S3 Bucket View Init."""
        super().__init__(request, const.RGW_S3_BUCKET_SERVICE)

    @CsmAuth.permissions({Resource.S3_BUCKET: {Action.UPDATE}})
    @Log.trace_method(Log.DEBUG)
    async def put(self):
        """
        PUT REST implementation for  s3 bucket.
        """
        Log.debug(f"Handling s3 bucket PUT request"
                  f" user_id: {self.request.session.credentials.user_id}")
        # Load Expected Bucket Schema
        operation = None
        operation_arguments = None
        try:
            # Validate Request Schema Body with BucketSchema
            input_body = await self.request.json()
            if "operation" not in input_body.keys() or "arguments" not in input_body.keys():
                 raise ValidationError("operation and arguments are required fields")
            operation = input_body['operation']
            if operation not in schemaFactory.operation_schema_map:
                raise ValidationError(f"{operation}: is not supported")
            operation_arguments = input_body['arguments']
            if not isinstance(operation_arguments, dict):
                raise ValidationError(f" operation_arguments is not of Type Dict :- {operation_arguments}")
            # Validation Operation Level Schema Validation
            schema = schemaFactory.init(operation)
            request_body = schema.load(operation_arguments)
            Log.debug(f"Handling s3 bucket PUT request"
                  f" request body: {request_body}")
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Invalid Request Body")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        # Call Service API and Return the Response
        with self._guard_service():
            response = await self._service.bucket_operation(operation, **request_body)
            return CsmResponse(response)
