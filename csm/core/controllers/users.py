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
from csm.core.blogic import const
from csm.core.controllers.view import CsmView
from csm.common.log import Log
from csm.common.errors import InvalidRequest


# TODO: find out about policies for names and passwords
class CsmUserCreateSchema(Schema):
    user_id = fields.Str(data_key='username', required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))
    roles = fields.List(fields.String())
    interfaces = fields.List(fields.String())
    temperature = fields.Str(default=None)
    language = fields.Str(default=None)
    timeout = fields.Int(default=None)

    @validates("user_id")
    def validate_quantity(self, value):
        if len(value) < const.CSM_USER_NAME_MIN_LEN:
            raise ValidationError("User name length must be greater than {}".format(
                const.CSM_USER_NAME_MIN_LEN))
        if len(value) > const.CSM_USER_NAME_MAX_LEN:
            raise ValidationError("User name length must not be greater than {}".format(
                const.CSM_USER_NAME_MAX_LEN))
        if not value.isalnum():
            raise ValidationError("User name must only contain alphanumeric characters")

class CsmGetUsersSchema(Schema):
    offset = fields.Int(validate=validate.Range(min=0), allow_none=True,
        default=None, missing=None)
    limit = fields.Int(default=None, validate=validate.Range(min=0), missing=None)
    sort_by = fields.Str(default="user_id", missing="user_id")
    sort_dir = fields.Str(validate=validate.OneOf(['desc', 'asc']),
        missing='asc', default='asc')


@CsmView._app_routes.view("/api/v1/user")
class CsmUsersListView(CsmView):
    def __init__(self, request):
        super(CsmUsersListView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching csm users
    """
    async def get(self):
        Log.debug("Handling csm users fetch request")
        csm_schema = CsmGetUsersSchema()
        try:
            request_data = csm_schema.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid Parameter for alerts", str(val_err))

        return await self._service.get_user_list(**request_data)

    """
    POST REST implementation for creating a csm user
    """
    async def post(self):
        Log.debug("Handling users post request")

        try:
            schema = CsmUserCreateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid request body: {}".format(val_err))

        return await self._service.create_user(**user_body)


@CsmView._app_routes.view("/api/v1/user/{user_id}")
class CsmUsersView(CsmView):
    def __init__(self, request):
        super(CsmUsersView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for csm account delete request
    """
    async def get(self):
        Log.debug("Handling get csm account request")
        user_id = self.request.match_info["user_id"]

        return await self._service.get_user(user_id)

    """
    DELETE REST implementation for csm account delete request
    """
    async def delete(self):
        Log.debug("Handling delete csm account request")
        user_id = self.request.match_info["user_id"]

        return await self._service.delete_user(user_id)

    """
    POST PUT implementation for creating a csm user
    """
    async def put(self):
        Log.debug("Handling users put request")
        user_id = self.request.match_info["user_id"]

        try:
            schema = CsmUserCreateSchema()
            user_body = schema.load(await self.request.json(), partial=True,
                unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid request body: {}".format(val_err))

        return await self._service.update_user(user_id, user_body)
