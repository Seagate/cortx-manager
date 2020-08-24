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

from marshmallow import Schema, fields, validate, ValidationError
from eos.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.core.controllers.schemas import FirmwareUpdateFileFieldSchema
from csm.core.controllers.validators import FileRefValidator
from csm.core.services.file_transfer import FileType, FileCache, FileRef
from csm.common.errors import CsmNotFoundError
from csm.common.conf import Conf
import os


class FirmwareUploadSchema(Schema):
    package = fields.Nested(FirmwareUpdateFileFieldSchema(), required=True)


@CsmView._app_routes.view("/api/v1/update/firmware/upload")
class FirmwarePackageUploadView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.FW_UPDATE_SERVICE]
        self._service_dispatch = {}

    """
    POST REST implementation to upload firmware packages
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def post(self):
        Log.debug(f"Handling firmware package upload api"
                 f" user_id: {self.request.session.credentials.user_id}")
        with FileCache() as cache:
            parsed_multipart = await self.parse_multipart_request(self.request, cache)
            try:
                multipart_data = FirmwareUploadSchema().load(parsed_multipart, unknown='EXCLUDE')
            except ValidationError as val_err:
                raise InvalidRequest(f"Invalid Package. {val_err}")
            package_ref = multipart_data['package']['file_ref']
            file_name = multipart_data['package']['filename']
            return await self._service.upload_package(package_ref, file_name)


@CsmView._app_routes.view("/api/v1/update/firmware/start")
class FirmwareUpdateView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.FW_UPDATE_SERVICE]

    """
    POST REST implementation to trigger firmware update
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def post(self):
        Log.debug(f"Handling firmware package update api"
                 f" user_id: {self.request.session.credentials.user_id}")
        availibility_status =  await self._service.check_for_package_availability()
        if availibility_status:
            return await self._service.start_update()


@CsmView._app_routes.view("/api/v1/update/firmware/status")
class FirmwareUpdateStatusView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.FW_UPDATE_SERVICE]
        self._service_dispatch = {}

    """
    GET REST implementation for getting current status of firmware update
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling get firmware update status api"
                 f" user_id: {self.request.session.credentials.user_id}")
        return await self._service.get_current_status()


@CsmView._app_routes.view("/api/v1/update/firmware/availability")
class FirmwarePackageAvailibility(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.FW_UPDATE_SERVICE]
        self._service_dispatch = {}

    """
    Get REST implementation to check package availability at given path.
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling get request to check firmware package availability status api"
                 f" user_id: {self.request.session.credentials.user_id}")
        return await self._service.check_for_package_availability()
