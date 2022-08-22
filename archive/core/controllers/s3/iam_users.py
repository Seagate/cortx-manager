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

from cortx.utils.log import Log
from typing import Dict
from marshmallow import (Schema, fields, ValidationError, validates_schema)
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.controllers.validators import (PathPrefixValidator,
                                             PasswordValidator,
                                             IamUserNameValidator)
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.s3.base import S3AuthenticatedView

class BaseSchema(Schema):
    """
    Base Class for IAM User Schema Validation
    """

    @staticmethod
    def format_error(validation_error_obj: ValidationError) -> str:
        """
        This Method will Format Validation Error messages to Proper Error messages.
        :param validation_error_obj: Validation Error Object :type: ValidationError
        :return: String for all Validation Error Messages
        """
        error_messages = []
        for each_key in validation_error_obj.messages.keys():
            error_messages.append(f"{each_key.capitalize()}: {''.join(validation_error_obj.messages[each_key])}")
        return "\n".join(error_messages)

class IamUserCreateSchema(BaseSchema):
    """
    IAM user Create schema validation class
    """
    user_name = fields.Str(required=True,
                           validate=[IamUserNameValidator()])
    password = fields.Str(required=True, validate=[PasswordValidator()])
    require_reset = fields.Boolean(default=False)

    @validates_schema
    def check_password(self, data: Dict, *args, **kwargs):
        if data["password"] == data["user_name"]:
            raise ValidationError(
                "Password should not be your username or email.",
                field_name="password")


class IamUserDeleteSchema(BaseSchema):
    """
    IAM user delete schema validation class
    """
    user_name = fields.Str(required=True, validate=[IamUserNameValidator()])

class IamUserPatchSchema(BaseSchema):
    """
    IAM user patch schema validation class
    """
    password = fields.Str(required=True, validate=[PasswordValidator()])


@CsmView._app_routes.view("/api/v1/iam_users")
@CsmView._app_routes.view("/api/v2/iam_users")
class IamUserListView(S3AuthenticatedView):
    def __init__(self, request):
        """
        Instantiation Method for Iam user view class
        """
        super().__init__(request, 's3_iam_users_service')

    @CsmAuth.permissions({Resource.S3IAMUSERS: {Action.LIST}})
    async def get(self):
        """
        Fetch list of IAM User's
        """
        Log.debug(f"Handling list IAM USER get request. "
                  f"user_id: {self.request.session.credentials.user_id}")
        # Execute List User Task
        with self._guard_service():
            return await self._service.list_users(self._s3_session)

    @CsmAuth.permissions({Resource.S3IAMUSERS: {Action.CREATE}})
    async def post(self):
        """
        Create's new IAM User.
        """
        schema = IamUserCreateSchema()
        Log.debug(f"Handling create IAM USER post request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            body = await self.request.json()
            request_data = schema.load(body, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        # Create User
        with self._guard_service():
            return await self._service.create_user(self._s3_session,
                                                   **request_data)


@CsmView._app_routes.view("/api/v1/iam_users/{user_name}")
@CsmView._app_routes.view("/api/v2/iam_users/{user_name}")
class IamUserView(S3AuthenticatedView):
    def __init__(self, request):
        """
        Instantiation Method for Iam user view class
        """
        super().__init__(request, 's3_iam_users_service')

    @CsmAuth.permissions({Resource.S3IAMUSERS: {Action.UPDATE}})
    async def patch(self):
        """
        Patch IAM user
        """
        Log.debug(f"Handling  IAM USER patch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        user_name = self.request.match_info["user_name"]
        try:
            schema = IamUserPatchSchema()
            patch_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        with self._guard_service():
            return await self._service.patch_user(self._s3_session, user_name, **patch_body)

    @CsmAuth.permissions({Resource.S3IAMUSERS: {Action.DELETE}})
    async def delete(self):
        """
        Delete IAM user
        """
        Log.debug(f"Handling  IAM USER delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        user_name = self.request.match_info["user_name"]
        if user_name == "root":
            raise InvalidRequest("Root IAM user cannot be deleted.")
        schema = IamUserDeleteSchema()
        try:
            schema.load({"user_name": user_name}, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(message_args=f"Invalid request body: {val_err}")
        # Delete Iam User
        with self._guard_service():
            return await self._service.delete_user(self._s3_session,
                                                   user_name)