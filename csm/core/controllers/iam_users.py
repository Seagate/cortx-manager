#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          iam_users.py
 Description:       Infrastructure for invoking business logic locally or
                    remotely or various available channels like REST.

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

import re
from typing import Dict
from marshmallow import Schema, fields, ValidationError, validates_schema, validate
from csm.core.blogic import const
from csm.core.controllers.view import CsmView
from csm.core.services.s3.iam_users import IamUsersService
from csm.common.errors import InvalidRequest

class BaseValidatorIamUser(Schema):
    @validates_schema
    def validate_password(self, data: Dict, *args, **kwargs):
        """
        Validates the password subbmitted in Api as per S3 Standards.
        :return:
        """

        # Check is password key exists else do not validates.
        try:
            password = data['password']
        except KeyError:
            return None

        if len(password) < 8:
            raise ValidationError(
                "Password must be of more than 8 characters.")
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                "Password must contain at least one Uppercase Alphabet.")
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                "Password must contain at least one Lowercase Alphabet.")
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                "Password must contain at least one Numeric value.")
        if not re.search(r"["+"\\".join(const.PASSWORD_SPECIAL_CHARACTER) + "]" , password):
            raise ValidationError(
                f"Password must include at lease one of the {''.join(const.PASSWORD_SPECIAL_CHARACTER)} characters.")
        if password == data.get('username', "") or password == data.get("email",
                                                                        ""):
            raise ValidationError(
                "Password should not be your username or email.")

class IamUserCreateSchema(BaseValidatorIamUser):
    user_name = fields.Str(required=True)
    password = fields.Str(required=True)
    path = fields.Str(default='/')
    require_reset = fields.Boolean(default=False)

class IamUserListSchema(BaseValidatorIamUser):
    path_prefix = fields.Str(default="/", validate=validate.Length(min=1, max=512))
    marker = fields.Str()
    max_items = fields.Integer()

class IamUserDeleteSchema(BaseValidatorIamUser):
    user_name = fields.Str(required=True)

@CsmView._app_routes.view("/api/v1/iam_users")
class IamUserView(CsmView):
    async def get(self):
        schema = IamUserDeleteSchema()
        try:
            schema.load(self.request.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            return InvalidRequest(str(val_err))
        iam_user_service_obj = IamUsersService()
        return await iam_user_service_obj.list_users()

    async def post(self):
        schema = IamUserCreateSchema()
        try:
            body = await self.request.json()
            schema.load(body, unknown='EXCLUDE')
        except ValidationError as val_err:
            return InvalidRequest(str(val_err))
        iam_user_service_obj = IamUsersService()
        return await iam_user_service_obj.create_user(**body)


@CsmView._app_routes.view("/api/v1/iam_users/{user_name}")
class IamUserSpecificView(CsmView):

    async def delete(self):
        user_name = self.request.match_info["user_name"]
        iam_user_service_obj = IamUsersService()
        return await iam_user_service_obj.delete_user

