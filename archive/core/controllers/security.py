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

from enum import Enum
from typing import Union
import os

import json
from marshmallow import fields, Schema
from marshmallow.exceptions import ValidationError

from csm.core.blogic import const
from csm.common.errors import CsmInternalError, CsmTypeError, InvalidRequest, CsmNotImplemented
from csm.core.services.file_transfer import FileCache
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.file_transfer import FileFieldSchema
from cortx.utils.log import Log
from csm.common.permission_names import Resource, Action
from csm.core.data.models.system_config import SecurityConfig


class TLSBundleSchema(Schema):
    pemfile = fields.Nested(FileFieldSchema())


class InstallSecurityBundleSchema(Schema):
    """
    Scheme for verification of PATCH request body for installation of secuirity bundle (pem file)

    """
    install = fields.Boolean(required=True)


class GetResponseBody:
    """Class represents GET REST API response body"""

    _STATUS = "status"
    _DATE = "date"
    _FILENAME = "filename"
    _SERIAL_NUMBER = "serial_number"

    def __init__(self, security_conf: Union[SecurityConfig, None]):
        self._security_conf = security_conf

    def to_response(self):
        if self._security_conf is None:
            return dict()

        filename = os.path.basename(self._security_conf.csm_config.pemfile_path)
        return {self._STATUS: self._security_conf.installation_status,
                self._DATE: str(self._security_conf.csm_config.date.isoformat()),
                self._FILENAME: filename,
                self._SERIAL_NUMBER: self._security_conf.csm_config.certificate_id}

    def __str__(self):
        return self.to_response()

@CsmView._app_routes.view("/api/v1/tls/bundle/upload")
@CsmView._app_routes.view("/api/v2/tls/bundle/upload")
class SecurityUploadView(CsmView):
    """ Security View for POST REST API implementation:
        1. Upload private key and corresponding certificate to the server

    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SECURITY_SERVICE]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.SECURITY: {Action.UPDATE}})
    async def post(self):
        """
        POST REST implementation for uploading private key and corresponding certificate

        :return:
        """
        Log.debug(f"Handling uploading TLS credentials POST method")
        with FileCache() as cache:
            # parse_multipart_request parse multipart request and returns dict
            # which maps multipart fields names to TextFieldSchema or FileFieldSchema
            parsed_multipart = await self.parse_multipart_request(self.request, cache)

            # validating parsed request
            try:
                multipart_data = TLSBundleSchema().load(parsed_multipart)
            except json.decoder.JSONDecodeError:
                raise InvalidRequest("Request body missing")
            except ValidationError as val_err:
                raise InvalidRequest(f"Invalid request body: {val_err}")

            # TODO: is it always granted that user_id is available during call of this method?
            user = self.request.session.credentials.user_id
            pemfile_name = multipart_data['pemfile']['filename']

            pemfile_ref = multipart_data['pemfile']['file_ref']
            try:
                await self._service.store_security_bundle(user, pemfile_name, pemfile_ref)
            except CsmTypeError as e:
                raise CsmInternalError("Wrong data") from e
            except CsmInternalError:
                raise  # throw the exception to the controller


@CsmView._app_routes.view("/api/v1/tls/bundle/install")
@CsmView._app_routes.view("/api/v2/tls/bundle/install")
class SecurityInstallView(CsmView):
    """ Security View for POST REST API implementation:
        1. Install lastly uploaded certificate

    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SECURITY_SERVICE]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.SECURITY: {Action.UPDATE}})
    async def post(self):
        """
        POST REST API implementation for enabling last uploaded certificate and trigger
        Provisioner API for certficate installation and services restarting
        """

        Log.debug(f"Handling certificate installation request. "
                  f"user_id: {self.request.session.credentials.user_id}")

        try:
            schema = InstallSecurityBundleSchema()
            patch_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        install = patch_body["install"]
        if not install:
            raise CsmNotImplemented(f"Invalid action for install={install}")

        if install:
            try:
                await self._service.install_certificate()
            except Exception as e:  # TODO:
                raise CsmInternalError(f"Internal error during certificate installation: {e}")


@CsmView._app_routes.view("/api/v1/tls/bundle/status")
@CsmView._app_routes.view("/api/v2/tls/bundle/status")
class SecurityStatusView(CsmView):
    """ Security View for GET REST API implementation:
        1. Get information about lastly uploaded certficate

    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SECURITY_SERVICE]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.SECURITY: {Action.READ}})
    async def get(self):
        """
        GET REST API implemenetation to return current certificate installation status
        """
        Log.debug(f"Handling get certificate installation status request. "
                  f"user_id: {self.request.session.credentials.user_id}")
        try:
            # NOTE: method returns SecurityConfig as status instance
            security_config = await self._service.get_certificate_installation_status()
        except Exception as e:
            raise CsmInternalError(f"Internal error during certificate installation: {e}")

        return GetResponseBody(security_config).to_response()

@CsmView._app_routes.view("/api/v1/tls/bundle/details")
@CsmView._app_routes.view("/api/v2/tls/bundle/details")
class SecurityDetailsView(CsmView):
    """ Security details for GET REST API implementation:
        1. Get certificate details
    """
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SECURITY_SERVICE]
        self._service_dispatch = {}

    @CsmAuth.permissions({Resource.SECURITY: {Action.READ}})
    async def get(self):
        """
        GET REST API implemenetation to return current certificate details
        """
        Log.debug(f"Handling get certificate details request. "
                  f"user_id: {self.request.session.credentials.user_id}")

        return await self._service.get_certificate_details()
        