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
from marshmallow import Schema, fields, validate, validates_schema
from marshmallow.exceptions import ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest, CsmPermissionDenied, CsmNotFoundError
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.validators import PasswordValidator, UserNameValidator, AccessKeyValidator
from csm.core.controllers.view import CsmView, CsmAuth, CsmResponse
from csm.core.controllers.s3.base import S3BaseView, S3AuthenticatedView


# TODO: find out about policies for names and passwords
class S3AccountCreationSchema(Schema):
    account_name = fields.Str(required=True, validate=[UserNameValidator()])
    account_email = fields.Email(required=True)
    password = fields.Str(required=True, validate=[PasswordValidator()])
    access_key = fields.Str(default=None, missing=None, validate=[AccessKeyValidator()])
    secret_key = fields.Str(default=None, missing=None,\
                                validate=validate.Length(min=8, max=40))

    @validates_schema
    def validate_access_secret_keys(self, data, **kwargs):
        if (data.get("access_key") is not None or data.get("secret_key") is not None) and \
            (data.get("access_key") is None or data.get("secret_key") is None):
            raise ValidationError("Either access_key or secret_key is not provided.")


class S3AccountPatchSchema(Schema):
    reset_access_key = fields.Boolean(default=False)
    password = fields.Str(required=True, validate=[PasswordValidator()])


@CsmView._app_routes.view("/api/v1/s3_accounts")
@CsmView._app_routes.view("/api/v2/s3_accounts")
class S3AccountsListView(S3BaseView):
    def __init__(self, request):
        super().__init__(request, const.S3_ACCOUNT_SERVICE)

    """
    GET REST implementation for S3 account fetch request
    """
    @CsmAuth.permissions({Resource.S3ACCOUNTS: {Action.LIST}})
    async def get(self):
        """Calling Stats Get Method"""
        Log.debug(f"Handling list s3 accounts fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        limit = self.request.rel_url.query.get("limit", None)
        marker = self.request.rel_url.query.get("continue", None)
        with self._guard_service():
            return await self._service.list_accounts(self.request.session.credentials,
                                                     marker, limit)

    """
    POST REST implementation for S3 account fetch request
    """
    @CsmAuth.permissions({Resource.S3ACCOUNTS: {Action.CREATE}})
    @Log.trace_method(Log.INFO)
    async def post(self):
        """Calling Stats Post Method"""
        Log.debug(f"Handling create s3 accounts post request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = S3AccountCreationSchema()
            account_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        # Check whether a CSM user with the same id already exists
        try:
            await self.request.app["csm_user_service"].get_user(account_body['account_name'])
        except CsmNotFoundError:
            # Ok, no CSM user has been found, now we can create an S3 account
            with self._guard_service():
                response = await self._service.create_account(**account_body)
                return CsmResponse(response, const.STATUS_CREATED)
        else:
            raise InvalidRequest("CSM user with same username already exists. S3 account name cannot be similar to an existing CSM user name")


@CsmView._app_routes.view("/api/v1/s3_accounts/{account_id}")
@CsmView._app_routes.view("/api/v2/s3_accounts/{account_id}")
class S3AccountsView(S3BaseView):
    def __init__(self, request):
        super().__init__(request, 's3_account_service')
        self.account_id = self.request.match_info["account_id"]
        if self._s3_session is not None and not self._s3_session.user_id == self.account_id:
            raise CsmPermissionDenied("Access denied. Cannot modify another S3 account.")

    """
    GET REST implementation for S3 account delete request
    """
    @CsmAuth.permissions({Resource.S3ACCOUNTS: {Action.DELETE}})
    async def delete(self):
        """Calling Stats Get Method"""
        Log.debug(f"Handling s3 accounts delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        with self._guard_service():
            response = await self._service.delete_account(self.account_id)
            await self.request.app.login_service.delete_all_sessions_for_user(self.account_id)
            return response

    """
    PATCH REST implementation for S3 account
    """
    @CsmAuth.permissions({Resource.S3ACCOUNTS: {Action.UPDATE}})
    async def patch(self):
        Log.debug(f"Handling update s3 accounts patch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = S3AccountPatchSchema()
            patch_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        with self._guard_service():
            response = await self._service.patch_account(self.account_id,
                                                         **patch_body)
            return response
