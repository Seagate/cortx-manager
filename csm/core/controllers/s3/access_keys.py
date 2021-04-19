#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          access_keys.py
 Description:       Controller-view implementation for S3 access keys management

 Creation Date:     08/17/2020
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from cortx.utils.log import Log
from marshmallow import Schema, fields, validate, ValidationError
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.s3.base import S3AuthenticatedView
from csm.core.controllers.validators import UserNameValidator
from csm.core.controllers.view import CsmView, CsmAuth


class CreateDeleteAccessKeyRelUrlSchema(Schema):
    user_name = fields.Str(required=False, validate=[UserNameValidator()])


class ListAccessKeysRelUrlSchema(Schema):
    marker = fields.Str(required=False, data_key='continue')
    limit = fields.Int(required=False)
    user_name = fields.Str(required=False, validate=[UserNameValidator()])


class PatchAccessKeySchema(Schema):
    status = fields.Str(
        required=True, validate=validate.OneOf(const.S3_ACCESS_KEY_STATUSES))
    user_name = fields.Str(required=False, validate=[UserNameValidator()])


@CsmView._app_routes.view("/api/v1/s3/access_keys")
@CsmView._app_routes.view("/api/v2/s3/access_keys")
class S3AccessKeysView(S3AuthenticatedView):

    def __init__(self, request):
        super().__init__(request, const.S3_ACCESS_KEYS_SERVICE)

    @CsmAuth.permissions({Resource.S3ACCESSKEYS: {Action.LIST}})
    async def get(self):
        """
        GET REST implementation for S3 access keys.
        """
        Log.debug(f'Handling S3 access keys GET request:'
                  f' user_id: {self.request.session.credentials.user_id}')
        try:
            request_url_data = ListAccessKeysRelUrlSchema().load(self.request.rel_url.query)
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request URL: {val_err}")
        with self._guard_service():
            # Gather all the access keys and filter out temporary keys created on each login
            login_service = self.request.app.login_service
            user_id = self.request.session.credentials.user_id
            tmp_keys = await login_service.get_temp_access_keys(user_id)
            resp = await self._service.list_access_keys(self._s3_session, **request_url_data)
            filtered_keys = [k for k in resp[const.S3_ACCESS_KEYS] if k[const.S3_ACCESS_KEY_ID] not in tmp_keys]
            resp[const.S3_ACCESS_KEYS] = filtered_keys
            # change the user_name, root to s3username in case of s3user request for accesskeys
            if request_url_data.get(const.USER_NAME) is None:
                for key in resp[const.S3_ACCESS_KEYS]:
                    if key[const.USER_NAME] == const.ROOT:
                        key[const.USER_NAME] = user_id
            return resp

    @CsmAuth.permissions({Resource.S3ACCESSKEYS: {Action.CREATE}})
    async def post(self):
        """
        POST REST implementation for S3 access keys.
        """
        Log.debug(f'Handling S3 access keys POST request:'
                  f' user_id: {self.request.session.credentials.user_id}')
        try:
            request_url_data = CreateDeleteAccessKeyRelUrlSchema().load(self.request.rel_url.query)
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request URL: {val_err}")
        with self._guard_service():
            return await self._service.create_access_key(self._s3_session, **request_url_data)


@CsmView._app_routes.view("/api/v1/s3/access_keys/{access_key_id}")
@CsmView._app_routes.view("/api/v2/s3/access_keys/{access_key_id}")
class S3AccessKeysListView(S3AuthenticatedView):

    def __init__(self, request):
        super().__init__(request, const.S3_ACCESS_KEYS_SERVICE)

    @CsmAuth.permissions({Resource.S3ACCESSKEYS: {Action.UPDATE}})
    async def patch(self):
        """
        PATCH REST implementation for S3 access key.
        """
        Log.debug(f'Handling S3 access key PATCH request:'
                  f' user_id: {self.request.session.credentials.user_id}')
        try:
            request_url_data = PatchAccessKeySchema().load(self.request.rel_url.query)
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        status = request_url_data.get('status')
        user_name = request_url_data.get('user_name', None)
        access_key_id = self.request.match_info['access_key_id']
        with self._guard_service():
            return await self._service.update_access_key(
                self._s3_session, access_key_id, status, user_name=user_name)

    @CsmAuth.permissions({Resource.S3ACCESSKEYS: {Action.DELETE}})
    async def delete(self):
        """
        DELETE REST implementation for S3 access key.
        """
        Log.debug(f'Handling S3 access key DELETE request:'
                  f' user_id: {self.request.session.credentials.user_id}')
        try:
            request_url_data = CreateDeleteAccessKeyRelUrlSchema().load(self.request.rel_url.query)
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request URL: {val_err}")
        access_key_id = self.request.match_info['access_key_id']
        with self._guard_service():
            return await self._service.delete_access_key(
                self._s3_session, access_key_id, **request_url_data)
