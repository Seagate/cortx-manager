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

from csm.core.services.file_transfer import FileType, FileCache
from csm.core.controllers.schemas import FileFieldSchema
from csm.core.controllers.view import CsmView
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.core.blogic import const

from aiohttp import web
from marshmallow import Schema, fields


class TextFieldSchema(Schema):
    content_type = fields.Str(required=True)
    content = fields.Str(required=True)


class CsmFileUploadSchema(Schema):
    description = fields.Nested(TextFieldSchema())
    image1 = fields.Nested(FileFieldSchema())
    image2 = fields.Nested(FileFieldSchema())


@CsmView._app_routes.view("/api/v1/csm/file/transfer")
@CsmView._app_routes.view("/api/v2/csm/file/transfer")
class CsmFileView(CsmView):
    """
    Not an active controller.

    If you want to test it
    add import of CsmFileView to src/core/controllers/__init__.py
    This is an example (not real API) on how to implement
    downloading and uploading functionality in controllers.
    "get" stands for download and "post" stands for upload.
    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["download_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for downloading file
    """
    async def get(self):
        """Show an example of handling download request."""
        Log.debug("Handling file download request")
        filename = self.request.rel_url.query.get("filename")

        if not filename:
            raise InvalidRequest("multipart header is absent")

        file_response = self._service.get_file_response(FileType.ETC_CSM, filename)
        return file_response

    """
    POST REST implementation for uploading file
    """
    async def post(self):
        """
        Show an example of post multipart request handler.

        We are expecting that request includes text field and file field.
        """
        # We use FileCache context manager if we expect a file in the incoming request
        with FileCache() as cache:

            # parse_multipart_request parse multipart request and returns dict
            # which maps multipart fields names to TextFieldSchema or FileFieldSchema
            parsed_multipart = await self.parse_multipart_request(self.request, cache)

            # validating parsed request
            multipart_data = CsmFileUploadSchema().load(parsed_multipart)

            # This is simple example of how we need save file
            image1_name = multipart_data['image1']['filename']
            image2_name = multipart_data['image2']['filename']

            image1 = multipart_data['image1']['file_ref']
            image2 = multipart_data['image2']['file_ref']

            image1.save_file(const.CSM_ETC_DIR, image1_name)
            image2.save_file(const.CSM_ETC_DIR, image2_name)

        return web.Response(text='Files uploaded')
