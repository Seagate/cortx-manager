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

from aiohttp import web
from json import JSONDecodeError
from marshmallow import Schema, ValidationError, fields
from typing import Dict

from cortx.utils.log import Log
from csm.common.errors import CsmError
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.services.usl_extensions import UslExtensionsService


class _View(CsmView):
    """
    Generic view class for USL API views. Binds a :class:`CsmView` instance to an USL service.
    """
    _extensions_service: UslExtensionsService

    def __init__(self, request: web.Request) -> None:
        CsmView.__init__(self, request)
        self._extensions_service = UslExtensionsService()
        self._s3_buckets_service = self._request.app[const.S3_BUCKET_SERVICE]


@CsmView._app_routes.view("/usl/v1/saas")
class SaaSURLView(_View):
    """
    Lyve Pilot SaaS URL view.
    """
    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.LIST}})
    async def get(self) -> Dict[str, str]:
        return await self._extensions_service.get_saas_url()


@CsmView._app_routes.view("/usl/v1/registerDevice")
class DeviceRegistrationView(_View):
    """
    Device registration view.
    """

    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.UPDATE}})
    async def post(self) -> None:

        class MethodSchema(Schema):
            class RegisterDeviceParams(Schema):
                url = fields.URL(required=True)
                reg_pin = fields.Str(attribute='regPin', data_key='regPin', required=True)
                reg_token = fields.Str(attribute='regToken', data_key='regToken', required=True)

            class AccessParams(Schema):
                class Credentials(Schema):
                    access_key = fields.Str(
                        attribute='accessKey', data_key='accessKey', required=True)
                    secret_key = fields.Str(
                        attribute='secretKey', data_key='secretKey', required=True)

                account_name = fields.Str(
                    attribute='accountName', data_key='accountName', required=True)
                # TODO validator
                uri = fields.URL(schemes=['s3'], required=True)
                credentials = fields.Nested(Credentials, required=True)

            class InternalCortxParams(Schema):
                bucket_name = fields.Str(
                    attribute='bucketName', data_key='bucketName', required=True)

            register_device_params = fields.Nested(
                RegisterDeviceParams,
                attribute='registerDeviceParams',
                data_key='registerDeviceParams',
                required=True,
            )
            access_params = fields.Nested(
                AccessParams, attribute='accessParams', data_key='accessParams', required=True)
            internal_cortx_params = fields.Nested(
                InternalCortxParams,
                attribute='internalCortxParams',
                data_key='internalCortxParams',
                required=True,
            )

        try:
            body = await self.request.json()
            registration_info = MethodSchema().load(body)
        except (JSONDecodeError, ValidationError) as e:
            desc = 'Malformed UDS registration payload'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        return await self._extensions_service.post_register_device(
            self._s3_buckets_service, registration_info)

    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.LIST}})
    async def get(self) -> None:
        await self._extensions_service.get_register_device()


@CsmView._app_routes.view("/usl/v1/registrationToken")
class RegistrationTokenView(_View):
    """
    Registration token generation view.
    """
    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.LIST}})
    async def get(self) -> Dict[str, str]:
        return await self._extensions_service.get_registration_token()
