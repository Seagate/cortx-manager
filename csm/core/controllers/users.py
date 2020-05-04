#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          users.py
 Description:       Implementation of users views

 Creation Date:     11/21/2019
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
from marshmallow import Schema, fields, validate, validates
from marshmallow.exceptions import ValidationError
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.core.controllers.validators import PasswordValidator, UserNameValidator
from eos.utils.log import Log
from csm.common.errors import InvalidRequest


class RolesList(fields.List):
    """
    A list of strings representing an role type.
    When deserialised, will be deduped"
    """

    def __init__(self, required=False, _validate=None, **kwargs):
        if _validate is not None:
            raise ValueError(
                "The RolesList field provides its own validation "
                "and thus does not accept a the 'validate' argument."
            )

        super().__init__(
            fields.String(validate=validate.OneOf(const.CSM_USER_ROLES)),
            required=required,
            validate=validate.Length(equal=1),
            allow_none=False,
            **kwargs,
        )

    def _deserialize(self, value, attr, data, **kwargs):
        # for unique entry of role
        return [ role
            for role in set(super()._deserialize(value, attr, data, **kwargs))
        ]

class CsmSuperUserCreateSchema(Schema):
    user_id = fields.Str(data_key='username', required=True,
                         validate=[UserNameValidator()])
    password = fields.Str(required=True, validate=[PasswordValidator()])


# TODO: find out about policies for names and passwords
class CsmUserCreateSchema(CsmSuperUserCreateSchema):
    roles = RolesList(required=True)

class CsmUserPatchSchema(Schema):
    old_password = fields.Str(validate=[PasswordValidator()])
    password = fields.Str(validate=[PasswordValidator()])
    roles = RolesList()

class GetUsersSortBy(fields.Str):
    def _deserialize(self, value, attr, data, **kwargs):
        if value == 'username':
            return 'user_id'
        return value


class CsmGetUsersSchema(Schema):
    offset = fields.Int(validate=validate.Range(min=0), allow_none=True,
                        default=None, missing=None)
    limit = fields.Int(default=None, validate=validate.Range(min=0), missing=None)
    sort_by = GetUsersSortBy(validate=validate.OneOf(['user_id',
                                                      'username',
                                                      'user_type',
                                                      'created_time',
                                                      'updated_time']),
                             default="user_id",
                             missing="user_id")
    sort_dir = fields.Str(validate=validate.OneOf(['desc', 'asc']),
                          missing='asc', default='asc')


@CsmView._app_routes.view("/api/v1/csm/users")
class CsmUsersListView(CsmView):
    def __init__(self, request):
        super(CsmUsersListView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching csm users
    """
    @CsmAuth.permissions({Resource.USERS: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling csm users fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        csm_schema = CsmGetUsersSchema()
        try:
            request_data = csm_schema.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid Parameter for alerts", str(val_err))
        users = await self._service.get_user_list(**request_data)
        return {'users': users}

    """
    POST REST implementation for creating a csm user
    """
    @CsmAuth.permissions({Resource.USERS: {Action.CREATE}})
    async def post(self):
        Log.debug(f"Handling users post request."
                  f" user_id: {self.request.session.credentials.user_id}")

        try:
            schema = CsmUserCreateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        s3_account = await self.request.app["s3_account_service"].get_account(
            user_body['user_id'])
        if s3_account is not None:
            raise InvalidRequest("S3 account with same name as passed CSM username alreay exists")

        response = await self._service.create_user(**user_body)
        return CsmResponse(response, const.STATUS_CREATED)


@CsmView._app_routes.view("/api/v1/csm/users/{user_id}")
class CsmUsersView(CsmView):
    def __init__(self, request):
        super(CsmUsersView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for csm account get request
    """
    @CsmAuth.permissions({Resource.USERS: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling get csm account request."
                  f" user_id: {self.request.session.credentials.user_id}")
        user_id = self.request.match_info["user_id"]
        return await self._service.get_user(user_id)

    """
    DELETE REST implementation for csm account delete request
    """
    @CsmAuth.permissions({Resource.USERS: {Action.DELETE}})
    async def delete(self):
        Log.debug(f"Handling delete csm account request."
                  f" user_id: {self.request.session.credentials.user_id}")
        user_id = self.request.match_info["user_id"]
        resp = await self._service.delete_user(user_id,
                                               self.request.session.credentials.user_id)
        # delete session for user
        # admin cannot be deleted         
        await self.request.app.login_service.delete_all_sessions_for_user(user_id)
        return resp

    """
    PATCH implementation for creating a csm user
    """
    @CsmAuth.permissions({Resource.USERS: {Action.UPDATE}})
    async def patch(self):
        Log.debug(f"Handling users patch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        user_id = self.request.match_info["user_id"]

        try:
            schema = CsmUserPatchSchema()
            user_body = schema.load(await self.request.json(), partial=True,
                                    unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        resp = await self._service.update_user(user_id, user_body,
                                               self.request.session.credentials.user_id)
        return resp

@CsmView._app_routes.view("/api/v1/preboarding/user")
@CsmAuth.public
class AdminUserView(CsmView):

    STATUS_CREATED = 201
    STATUS_CONFLICT = 409

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["csm_user_service"]

    async def post(self):
        """
        POST REST implementation of creating a super user for preboarding
        """
        Log.debug("Creating super user")

        try:
            schema = CsmSuperUserCreateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(message_args=f"Invalid request body: {val_err}")

        status = const.STATUS_CREATED
        response = await self._service.create_super_user(**user_body)
        if not response:
            status = const.STATUS_CONFLICT
            response = {
                'message_id': 'root_already_exists',
                'message_text': 'Root user already exists',
                'extended_message': user_body['user_id']
            }

        # TODO: We need to return specific HTTP codes here.
        # Change this after we have proper exception hierarchy.
        return CsmResponse(response, status=status)
