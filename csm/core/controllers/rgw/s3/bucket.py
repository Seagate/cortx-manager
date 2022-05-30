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
from marshmallow import fields, ValidationError, validate
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth, CsmResponse
from csm.core.controllers.validators import ValidationErrorFormatter, ValidateSchema
from csm.core.controllers.rgw.s3.base import S3BaseView
from csm.common.errors import ServiceError


class BucketBaseSchema(ValidateSchema):
    """
    S3 Bucket First Level schema validation class.

    Operation and arguments are required keys
    """

    operation = fields.Str(data_key=const.ARG_OPERATION, required=True,
                           validate=validate.OneOf(const.SUPPORTED_BUCKET_OPERATIONS))
    arguments = fields.Dict(data_key=const.ARG_ARGUMENTS, keys=fields.Str(),
                            values=fields.Raw(allow_none=True), required=True)


class LinkBucketSchema(ValidateSchema):
    """
    S3 bucket operation's Second Level Schema Validation.

    S3 Bucket Link schema validation class.
    """

    uid = fields.Str(data_key=const.UID, required=True)
    bucket = fields.Str(data_key=const.BUCKET, required=True)
    bucket_id = fields.Str(data_key=const.BUCKET_ID, missing=None, allow_none=False)


class UnlinkBucketSchema(ValidateSchema):
    """
    S3 bucket operation's Second Level Schema Validation.

    S3 Bucket Unlink schema validation class.
    """

    uid = fields.Str(data_key=const.UID, required=True)
    bucket = fields.Str(data_key=const.BUCKET, required=True)


class SchemaFactory:
    @staticmethod
    def init(operation):
        operation_schema_map = {
            const.LINK: LinkBucketSchema,
            const.UNLINK: UnlinkBucketSchema
        }
        return operation_schema_map[operation]()


@CsmView._app_routes.view("/api/v2/s3/bucket")
class S3BucketView(S3BaseView):
    """
    S3 Bucket View for REST API implementation.

    PUT: Bucket Opertation
    """

    def __init__(self, request):
        """S3 Bucket View Init."""
        super().__init__(request, const.S3_BUCKET_SERVICE)

    @CsmAuth.permissions({Resource.S3_BUCKET: {Action.UPDATE}})
    @Log.trace_method(Log.DEBUG)
    async def put(self):
        """PUT REST implementation for  s3 bucket."""
        Log.info(f"Handling s3 bucket PUT request"
                 f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = BucketBaseSchema()
            request_body = schema.load(await self.request.json())
            operation = request_body.get(const.ARG_OPERATION)
            operation_arguments = request_body.get(const.ARG_ARGUMENTS)
            operation_schema = SchemaFactory.init(operation)
            operation_request_body = operation_schema.load(operation_arguments)
            Log.debug(f"Handling s3 bucket PUT request"
                      f" request operation: {operation}"
                      f" request operation body: {operation_request_body}")
        except json.decoder.JSONDecodeError:
            raise InvalidRequest("Could not parse request body, invalid JSON received.")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        with ServiceError.guard_service():
            response = await self._service.execute(operation, **operation_request_body)
            return CsmResponse(response)
