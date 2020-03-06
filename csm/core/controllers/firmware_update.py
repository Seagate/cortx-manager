#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          upgrade.py
 Description:       Controller for handling system upgrade 

 Creation Date:     02/25/2020
 Author:            Udayan Yaragattikar

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
from csm.common.log import Log
from csm.core.controllers.validators import FileRefValidator
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.common.errors import InvalidRequest
from csm.core.blogic import const

from aiohttp import web
from marshmallow import Schema, fields, validate, exceptions


class FileFieldSchema(Schema):
    """ Validation schema for uploaded files"""
    content_type = fields.Str(required=True)
    filename = fields.Str(required=True)
    file_ref = fields.Field(validate=FileRefValidator())


class FirmwareUploadSchema(Schema):
    package = fields.Nested(FileFieldSchema(), required=True)


@CsmView._app_routes.view("/api/v1/firmware/upload")
class FirmwarePackageUploadView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["fw_update_service"]
        self._service_dispatch = {}

    """
    POST REST implementation to upload firmware packages
    """
    async def post(self):
        Log.debug(f"Handling firmware package upload api"
                  f" user_id: {self.request.session.credentials.user_id}")
        with FileCache() as cache:
            parsed_multipart = await self.parse_multipart_request(self.request, cache)
            multipart_data = FirmwareUploadSchema().load(parsed_multipart, unknown='EXCLUDE')
            package_ref = multipart_data['package']['file_ref']
            file_name = multipart_data['package']['filename']
            return await self._service.firmware_package_upload(package_ref, file_name)

@CsmView._app_routes.view("/api/v1/firmware/update")
class FirmwareUpdateView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["fw_update_service"]
        self._service_dispatch = {}

    """
    POST REST implementation to trigger firmware update
    """
    async def post(self):
        Log.debug(f"Handling firmware package update api"
                  f" user_id: {self.request.session.credentials.user_id}")
        return await self._service.trigger_firmware_upload()

