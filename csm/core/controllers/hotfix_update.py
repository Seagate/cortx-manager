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
from csm.core.controllers.schemas import HotFixFileFieldSchema
from csm.core.controllers.validators import FileRefValidator
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.common.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const

from aiohttp import web
from marshmallow import Schema, fields, validate, exceptions


class HotFixUploadSchema(Schema):
    package = fields.Nested(HotFixFileFieldSchema(), required=True)


@CsmView._app_routes.view("/api/v1/upgrade/hotfix/upload")
class CsmHotfixUploadView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.HOTFIX_UPDATE_SERVICE]
        self._service_dispatch = {}

    """
    POST REST implementation for uploading hotfix packages
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def post(self):
        with FileCache() as cache:
            parsed_multipart = await self.parse_multipart_request(self.request, cache)
            multipart_data = HotFixUploadSchema().load(parsed_multipart, unknown='EXCLUDE')

            package_ref = multipart_data['package']['file_ref']
            return await self._service.upload_package(package_ref)


@CsmView._app_routes.view("/api/v1/upgrade/hotfix/start")
class CsmHotfixStartView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.HOTFIX_UPDATE_SERVICE]
        self._service_dispatch = {}

    """
    POST REST implementation for starting a hotfix update
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def post(self):
        return await self._service.start_upgrade()


@CsmView._app_routes.view("/api/v1/upgrade/hotfix/status")
class CsmHotfixStatusView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.HOTFIX_UPDATE_SERVICE]
        self._service_dispatch = {}

    """
    GET REST implementation for starting a hotfix update
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.LIST}})
    async def get(self):
        return await self._service.get_current_status()
