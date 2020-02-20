#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          upgrade.py
 Description:       Controller for handling system upgrade 

 Creation Date:     02/20/2020
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


import asyncio

from csm.core.services.file_transfer import FileType, FileCache, FileRef
from csm.core.controllers.validators import FileRefValidator
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.common.log import Log
from csm.common.errors import InvalidRequest
from csm.core.blogic import const

from aiohttp import web
from marshmallow import Schema, fields, validate, exceptions


class FileFieldSchema(Schema):
    content_type = fields.Str(required=True)
    filename = fields.Str(required=True)
    file_ref = fields.Field(validate=FileRefValidator())


class CsmFileUploadSchema(Schema):
    package = fields.Nested(FileFieldSchema(), required=True)


@CsmView._app_routes.view("/api/v1/upgrade/hotfix/upload")
class CsmHotfixUploadView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["hotfix_service"]
        self._service_dispatch = {}

    """
    POST REST implementation for uploading hotfix packages
    """
    async def post(self):
        # We use FileCache context manager if we expect a file in the incoming request
        with FileCache() as cache:

            # parse_multipart_request parse multipart request and returns dict 
            # which maps multipart fields names to TextFieldSchema or FileFieldSchema
            parsed_multipart = await self.parse_multipart_request(self.request, cache)

            # validating parsed request
            multipart_data = CsmFileUploadSchema().load(parsed_multipart, unknown='EXCLUDE')

            # This is simple example of how we need save file
            package_name = multipart_data['package']['filename']
            package_ref = multipart_data['package']['file_ref']

            info = await self._service.upload_package(package_ref)
            return info

@CsmView._app_routes.view("/api/v1/upgrade/hotfix/start")
class CsmHotfixStartView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["hotfix_service"]
        self._service_dispatch = {}

    """
    POST REST implementation for starting a hotfix update
    """
    async def post(self):
        await self._service.start_upgrade()
        return web.Response(text='OK')
