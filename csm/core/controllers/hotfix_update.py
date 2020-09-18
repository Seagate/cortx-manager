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

import asyncio

from csm.core.services.file_transfer import FileType, FileCache, FileRef
from csm.core.controllers.schemas import HotFixFileFieldSchema
from csm.core.controllers.validators import FileRefValidator
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const

from aiohttp import web
from marshmallow import Schema, fields, validate, exceptions


class HotFixUploadSchema(Schema):
    package = fields.Nested(HotFixFileFieldSchema(), required=True)


@CsmView._app_routes.view("/api/v1/update/hotfix/upload")
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
            file_name = multipart_data['package']['filename']
            return await self._service.upload_package(package_ref, file_name)


@CsmView._app_routes.view("/api/v1/update/hotfix/start")
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
        return await self._service.start_update()


@CsmView._app_routes.view("/api/v1/update/hotfix/status")
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
