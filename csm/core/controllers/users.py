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
from marshmallow import Schema, fields, validate, pre_load, post_load
from marshmallow.exceptions import ValidationError
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.core.controllers.validators import PasswordValidator, UserNameValidator
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest


class CsmUserCreateSchema(Schema):
    user_id = fields.Str(data_key='username', required=True,
                         validate=[UserNameValidator()])
    password = fields.Str(required=True, validate=[PasswordValidator()])
    email = fields.Email(required=True)
    role = fields.Str(required=True, validate=validate.OneOf(const.CSM_USER_ROLES))


class CsmUserPatchSchema(Schema):
    current_password = fields.Str(validate=[PasswordValidator()])
    password = fields.Str(validate=[PasswordValidator()])
    user_role = fields.Str(data_key='role', validate=validate.OneOf(const.CSM_USER_ROLES))
    email_address = fields.Email(data_key='email')
    reset_password = fields.Bool(required=False)

    @pre_load
    def pre_load(self, data, **kwargs):
        """Validate PATCH body pre  marshamallow validation."""
        if const.CSM_USER_NAME in data:
            raise InvalidRequest("username cannot be modified")
        return data

    @post_load
    def post_load(self, data, **kwargs):
        """Validate PATCH body for no operation post marshamallow validation."""
        # empty body is invalid request
        if not data:
            raise InvalidRequest("Insufficient information in request body")

        # just current_password in body is invalid
        if len(data) == 1 and const.CSM_USER_CURRENT_PASSWORD in data:
            Log.debug(f"User cannot be modified with only current_password field: {self.current_password}")
            raise InvalidRequest(f"Insufficient information in request body {data}")
        return data

class GetUsersSortBy(fields.Str):
    def _deserialize(self, value, attr, data, **kwargs):
        if value == 'username':
            return 'user_id'
        return value

class CsmGetUsersSchema(Schema):
    offset = fields.Int(validate=validate.Range(min=0), allow_none=True,
                        default=None, missing=None)
    limit = fields.Int(default=None, validate=validate.Range(min=0), missing=None)
    sort_by = GetUsersSortBy(data_key='sortby',
                             validate=validate.OneOf(const.CSM_USER_SORTABLE_FIELDS),
                             default="user_id",
                             missing="user_id")
    sort_dir = fields.Str(data_key='dir', validate=validate.OneOf(['desc', 'asc']),
                          missing='asc', default='asc')
    username = fields.Str(
        default=None, missing=None,
        validate=validate.Length(min=1, max=const.CSM_USER_NAME_MAX_LEN))
    role = fields.Str(default=None, missing=None)


@CsmView._app_routes.view("/api/v1/csm/users")
@CsmView._app_routes.view("/api/v2/system/users")
class CsmUsersListView(CsmView):
    def __init__(self, request):
        super(CsmUsersListView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.USERS: {Action.LIST}})
    async def get(self):
        """GET REST implementation for fetching csm users."""
        Log.info(
            f"[{self.request.request_id}] Processing request: {self.request.method} {self.request.path}"\
            f" User: {self.request.session.credentials.user_id}")
        csm_schema = CsmGetUsersSchema()
        try:
            request_data = csm_schema.load(self.request.rel_url.query, unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(str(val_err))
        users = await self._service.get_user_list(**request_data)
        Log.info(
            f"[{self.request.request_id}] Processed request: {self.request.method} {self.request.path}"\
            f" User: {self.request.session.credentials.user_id}")
        return CsmResponse({'users': users})

    @CsmAuth.permissions({Resource.USERS: {Action.CREATE}})
    async def post(self):
        """POST REST implementation for creating a csm user."""
        creator = self.request.session.credentials.user_id if self.request.session else None
        Log.info(
            f"[{self.request.request_id}] Processing request: {self.request.method} {self.request.path}"\
            f" User: {creator}")
        try:
            schema = CsmUserCreateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(const.JSON_ERROR)
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        # TODO: Story has been taken for unsupported services
        # The following commented lines will be removed by above story
        # s3_account = await self.request.app["s3_account_service"].get_account(
        #    user_body['user_id'])
        # if s3_account is not None:
        #    raise InvalidRequest("S3 account with same name as passed CSM username already exists")

        user_body['creator_id'] = creator
        response = await self._service.create_user(**user_body)
        Log.info(
            f"[{self.request.request_id}] Processed request: {self.request.method} {self.request.path}"\
            f" User: {creator}")
        return CsmResponse(response, const.STATUS_CREATED)


@CsmView._app_routes.view("/api/v1/csm/users/{user_id}")
@CsmView._app_routes.view("/api/v2/system/users/{user_id}")
class CsmUsersView(CsmView):
    def __init__(self, request):
        super(CsmUsersView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.USERS: {Action.LIST}})
    async def get(self):
        """GET REST implementation for csm account get request."""
        Log.info(
            f"[{self.request.request_id}] Processing request: {self.request.method} {self.request.path}"\
            f" User: {self.request.session.credentials.user_id}")
        user_id = self.request.match_info["user_id"]
        resp = await self._service.get_user(user_id)
        Log.info(
            f"[{self.request.request_id}] Processed request: {self.request.method} {self.request.path}"\
            f" User: {self.request.session.credentials.user_id}")
        return CsmResponse(resp)

    @CsmAuth.permissions({Resource.USERS: {Action.DELETE}})
    async def delete(self):
        """DELETE REST implementation for csm account delete request."""
        loggedin_user_id = self.request.session.credentials.user_id
        Log.info(
            f"[{self.request.request_id}] Processing request: {self.request.method} {self.request.path}"\
            f" User: {loggedin_user_id}")
        user_id = self.request.match_info["user_id"]
        resp = await self._service.delete_user(user_id, loggedin_user_id)
        # TODO: check if the user has really been deleted
        # delete session for user
        # admin cannot be deleted
        await self.request.app.login_service.delete_all_sessions_for_user(user_id)
        Log.info(
            f"[{self.request.request_id}] Processed request: {self.request.method} {self.request.path}"\
            f" User: {loggedin_user_id}")
        return CsmResponse(resp)

    @CsmAuth.permissions({Resource.USERS: {Action.UPDATE}})
    async def patch(self):
        """PATCH implementation for creating a csm user."""
        loggedin_user_id = self.request.session.credentials.user_id
        Log.info(
            f"[{self.request.request_id}] Processing request: {self.request.method} {self.request.path}"\
            f" User: {loggedin_user_id}")
        user_id = self.request.match_info["user_id"]

        try:
            schema = CsmUserPatchSchema()
            user_body = schema.load(await self.request.json(), partial=True,
                                    unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(const.JSON_ERROR)
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        resp = await self._service.update_user(
            user_id, user_body, loggedin_user_id)
        Log.info(
            f"[{self.request.request_id}] Processed request: {self.request.method} {self.request.path}"\
            f" User: {loggedin_user_id}")
        return CsmResponse(resp)
