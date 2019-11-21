#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          s3_iam_users.py
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

from marshmallow import (Schema, fields, ValidationError, validate, validates_schema)
from csm.core.blogic.validators import StartsWith, Password
from csm.core.controllers.view import CsmView
from csm.core.providers.providers import Response

class BaseSchema(Schema):
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
    user_name = fields.Str(required=True, validate=validate.Length(min=1,  max=64))
    password = fields.Str(required=True, validate=[validate.Length(min=8, max=64), Password()])
    path = fields.Str(default='/', validate=validate.Length(max=512))
    require_reset = fields.Boolean(default=False)

    @validates_schema
    def check_password(self, data, *args, **kwargs):
        if data["password"] == data["user_name"]:
            raise ValidationError("Password should not be your username or email.", field_name="password")

class IamUserListSchema(BaseSchema):
    path_prefix = fields.Str(default="/", validate=[validate.Length(max=512), StartsWith("/", True)])

class IamUserDeleteSchema(BaseSchema):
    user_name = fields.Str(required=True, validate=validate.Length(min=1, max=64))

@CsmView._app_routes.view("/api/v1/iam_users")
class IamUserListView(CsmView):
    def __init__(self, request):
        """
        Instantiation Method for Iam user view class
        """
        super(IamUserListView, self).__init__(request)
        # Fetch S3 access_key, secret_key and session_token from session
        self._s3_session = {"access_key_id": "sbuYSnuPT4KMA35wjzqU-g", "secret_key_id": "//8HG/nhb45J+Z9s8A4xqAAW8pGD4SDs25dFvtTU",
                      "session_token": "Gok8y3lL4XYhM0vR4Fg4m31ZJSj03h4zswp/4x+m"}  # self.request.session.data.s3_session
        if not self._s3_session:
            raise Response(rc=401, output="This user is not an S3 User")


    async def get(self):
        """
        Fetch list of IAM User's
        """
        schema = IamUserListSchema()
        try:
            data = schema.load(dict(self.request.query), unknown='EXCLUDE')
        except ValidationError as val_err:
            return Response(rc=400,
                            output=schema.format_error(val_err))
        # Execute List User Task
        _service = await self.request.app["s3_iam_users_service"]
        return await _service.list_users(**data, s3_session=self._s3_session)

    async def post(self):
        """
        Create's new IAM User.
        """
        schema = IamUserCreateSchema()
        try:
            body = await self.request.json()
            request_data = schema.load(body, unknown='EXCLUDE')
        except ValidationError as val_err:
            return Response(rc=400,
                            output=schema.format_error(val_err))
        # Create User
        _service = await self.request.app["s3_iam_users_service"]
        return await self._service.create_user(**request_data)

@CsmView._app_routes.view("/api/v1/iam_users/{user_name}")
class IamUserView(CsmView):
    def __init__(self, request):
        """
        Instantiation Method for Iam user view class
        """
        super(IamUserView, self).__init__(request)
        # Fetch S3 access_key, secret_key and session_token from session
        s3_session = {"access_key_id": "sbuYSnuPT4KMA35wjzqU-g",
                      "secret_key_id": "//8HG/nhb45J+Z9s8A4xqAAW8pGD4SDs25dFvtTU",
                      "session_token": "Gok8y3lL4XYhM0vR4Fg4m31ZJSj03h4zswp/4x+m"}  # self.request.session.data.s3_session
        if not s3_session:
            raise Response(rc=401, output="This user is not an S3 User")

    async def delete(self):
        """
        Delete IAM user
        """
        user_name = self.request.match_info["user_name"]
        schema = IamUserDeleteSchema()
        try:
            schema.load({"user_name": user_name}, unknown='EXCLUDE')
        except ValidationError as val_err:
            return Response(rc=400,
                            output=schema.format_error(val_err))
        # Delete Iam User
        _service = await self.request.app["s3_iam_users_service"]
        return await _service.delete_user(user_name)
