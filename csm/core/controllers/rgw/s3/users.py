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
from marshmallow import Schema, fields, ValidationError, validate, validates_schema
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth, CsmResponse
from csm.core.controllers.validators import ValidationErrorFormatter
from csm.core.controllers.rgw.s3.base import S3BaseView

class S3IAMusersBaseSchema(Schema):
    """Base Class for S3 IAM User Schema Validation"""

    @validates_schema
    def invalidate_empty_values(self, data, **kwargs):
        """This method invalidates the empty strings."""
        for key, value in data.items():
            if value is not None and not str(value).strip():
                raise ValidationError(f"{key}: Can not be empty")

class UserCreateSchema(S3IAMusersBaseSchema):
    """S3 IAM User create schema validation class."""

    uid = fields.Str(data_key=const.RGW_JSON_UID, required=True)
    display_name = fields.Str(data_key=const.RGW_JSON_DISPLAY_NAME, required=True)
    email = fields.Email(data_key=const.RGW_JSON_EMAIL, missing=None)
    key_type = fields.Str(data_key=const.RGW_JSON_KEY_TYPE, missing=None,
                    validate=validate.OneOf(['s3']))
    access_key = fields.Str(data_key=const.RGW_JSON_ACCESS_KEY, missing=None)
    secret_key = fields.Str(data_key=const.RGW_JSON_SECRET_KEY, missing=None)
    user_caps = fields.Str(data_key=const.RGW_JSON_USER_CAPS, missing=None)
    generate_key = fields.Bool(data_key=const.RGW_JSON_GENERATE_KEY, missing=None)
    max_buckets = fields.Int(data_key=const.RGW_JSON_MAX_BUCKETS, missing=None)
    suspended = fields.Bool(data_key=const.RGW_JSON_SUSPENDED, missing=None)
    tenant = fields.Str(data_key=const.RGW_JSON_TENANT, missing=None)

class UserGetSchema(S3IAMusersBaseSchema):
    """S3 IAM User get schema validation class."""

    uid = fields.Str(data_key=const.RGW_JSON_UID, required=True)

class UserDeleteSchema(S3IAMusersBaseSchema):
    """S3 IAM User delete schema validation class."""

    uid = fields.Str(data_key=const.RGW_JSON_UID, required=True)
    purge_data = fields.Bool(data_key=const.RGW_JSON_PURGE_DATA, missing=None)

@CsmView._app_routes.view("/api/v2/s3/iam/users")
class S3IAMUserListView(S3BaseView):
    """
    S3 IAM User List View for REST API implementation.

    PUT: Create a new user
    """

    def __init__(self, request):
        """S3 IAM User List View Init."""
        super().__init__(request)
        self._service = self.request.app[const.RGW_S3_IAM_USERS_SERVICE]

    @CsmAuth.permissions({Resource.S3_IAM_USERS: {Action.CREATE}})
    @Log.trace_method(Log.DEBUG)
    async def put(self):
        """
        PUT REST implementation for creating a new s3 iam user.
        """
        Log.debug(f"Handling create s3 iam user PUT request"
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = UserCreateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
            Log.debug(f"Handling create s3 iam user PUT request"
                  f" request body: {user_body}")
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Invalid Request Body")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        with self._guard_service():
            response = await self._service.create_user(**user_body)
            return CsmResponse(response)

    @CsmAuth.permissions({Resource.S3_IAM_USERS: {Action.LIST}})
    @Log.trace_method(Log.DEBUG)
    async def get(self):
        """
        GET REST implementation for fetching existing s3 iam user.
        """
        Log.debug(f"Handling get s3 iam user GET request"
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = UserGetSchema()
            request_body = schema.load(await self.request.json(), unknown='EXCLUDE')
            Log.debug(f"Handling get s3 iam user GET request"
                  f" request body: {request_body}")
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Invalid Request Body")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        with self._guard_service():
            response = await self._service.get_user(**request_body)
            return CsmResponse(response)

    @CsmAuth.permissions({Resource.S3_IAM_USERS: {Action.DELETE}})
    @Log.trace_method(Log.DEBUG)
    async def delete(self):
        """
        DELETE REST implementation for deleting existing s3 iam user.
        """
        Log.debug(f"Handling delete s3 iam user DELETE request"
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = UserDeleteSchema()
            request_body = schema.load(await self.request.json(), unknown='EXCLUDE')
            Log.debug(f"Handling create s3 iam user DELETE request"
                  f" request body: {request_body}")
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Invalid Request Body")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        with self._guard_service():
            response = await self._service.delete_user(**request_body)
            return CsmResponse(response)
