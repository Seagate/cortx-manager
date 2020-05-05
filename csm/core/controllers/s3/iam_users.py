#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          iam_users.py
 Description:       Handles Routing for various operations done on S3 IAM users.

 Creation Date:     13/11/2019
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from eos.utils.log import Log
from typing import Dict
from marshmallow import (Schema, fields, ValidationError, validates_schema)
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.controllers.validators import (PathPrefixValidator,
                                             PasswordValidator,
                                             UserNameValidator)
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
                           validate=[UserNameValidator()])
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
    user_name = fields.Str(required=True, validate=[UserNameValidator()])


@CsmView._app_routes.view("/api/v1/iam_users")
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
            raise InvalidRequest(message_args=f"Invalid request body: {val_err}")
        # Create User
        with self._guard_service():
            return await self._service.create_user(self._s3_session,
                                                   **request_data)


@CsmView._app_routes.view("/api/v1/iam_users/{user_name}")
class IamUserView(S3AuthenticatedView):
    def __init__(self, request):
        """
        Instantiation Method for Iam user view class
        """
        super().__init__(request, 's3_iam_users_service')

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
