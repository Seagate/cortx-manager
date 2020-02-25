#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          stats.py
 Description:       Implementation of stats view

 Creation Date:     11/15/2019
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
from marshmallow import Schema, fields, validate
from csm.core.controllers.validators import PasswordValidator, UserNameValidator
from marshmallow.exceptions import ValidationError
from csm.core.controllers.view import CsmView
from csm.core.controllers.s3.base import S3AuthenticatedView
from csm.common.log import Log
from csm.common.errors import InvalidRequest, CsmPermissionDenied


# TODO: find out about policies for names and passwords
class S3AccountCreationSchema(Schema):
    account_name = fields.Str(required=True, validate=[UserNameValidator()])
    account_email = fields.Email(required=True)
    password = fields.Str(required=True, validate=[PasswordValidator()])


class S3AccountPatchSchema(Schema):
    reset_access_key = fields.Boolean(default=False)
    password = fields.Str(required=True, validate=[PasswordValidator()])


@CsmView._app_routes.view("/api/v1/s3_accounts")
class S3AccountsListView(CsmView):
    def __init__(self, request):
        super(S3AccountsListView, self).__init__(request)
        self._service = self.request.app["s3_account_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for S3 account fetch request
    """
    async def get(self):
        """Calling Stats Get Method"""
        Log.debug(f"Handling list s3 accounts fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        limit = self.request.rel_url.query.get("limit", None)
        marker = self.request.rel_url.query.get("continue", None)
        return await self._service.list_accounts(marker, limit)

    """
    POST REST implementation for S3 account fetch request
    """
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
        return await self._service.create_account(**account_body)


@CsmView._app_routes.view("/api/v1/s3_accounts/{account_id}")
class S3AccountsView(S3AuthenticatedView):
    def __init__(self, request):
        super().__init__(request, 's3_account_service')
        if not self._s3_session.user_id == self.account_id:
            raise CsmPermissionDenied("Access denied. Verify account name.")

    """
    GET REST implementation for S3 account delete request
    """
    async def delete(self):
        """Calling Stats Get Method"""
        Log.debug(f"Handling s3 accounts delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        account_id = self.request.match_info["account_id"]
        response_obj = await self._service.delete_account(self._s3_session, account_id)
        if not response_obj:
            await self.request.app.login_service.delete_all_sessions(
            self.request.session.session_id)
        return response_obj

    """
    PATCH REST implementation for S3 account
    """
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
        response_obj =  await self._service.patch_account(self._s3_session,
                                            self.account_id, **patch_body)
        if response_obj:
            await self.request.app.login_service.delete_all_sessions(self.request.session.session_id)
        return response_obj
