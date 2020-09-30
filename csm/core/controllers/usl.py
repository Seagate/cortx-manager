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
from ipaddress import ip_address
from json import JSONDecodeError
from marshmallow import Schema, ValidationError, fields, validates
from typing import Any, Dict, List, Type

from csm.common.decorators import Decorators
from csm.common.errors import CsmError, CsmPermissionDenied, CsmNotFoundError
from cortx.utils.log import Log
from csm.common.conf import Conf
from csm.common.permission_names import Resource, Action
from csm.common.runtime import Options
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.usl_access_parameters_schema import AccessParamsSchema


# TODO replace this workaround with a proper firewall, or serve USL on a separate socket
class _Proxy:
    @staticmethod
    def on_loopback_only(cls: Type['_View']) -> Type['_View']:

        old_init = cls.__init__

        def new_init(obj, request: web.Request) -> None:
            if request.transport is not None:
                peername = request.transport.get_extra_info('peername')
                if (peername is None or
                    peername[0] is None or
                    not ip_address(peername[0]).is_loopback
                ):
                    raise web.HTTPNotFound()
            old_init(obj, request)

        setattr(cls, '__init__', new_init)
        return cls


class _View(CsmView):
    """
    Generic view class for USL API views. Binds a :class:`CsmView` instance to an USL service.
    """
    def __init__(self, request: web.Request) -> None:
        CsmView.__init__(self, request)
        self._service = self._request.app[const.USL_SERVICE]
        self._s3_account_service = self._request.app[const.S3_ACCOUNT_SERVICE]


class _SecuredView(_View):
    """
    USL API view secured by the USL API key
    """

    USL_API_KEY_HTTP_HEAD = 'X-API-KEY'

    def __init__(self, request: web.Request) -> None:
        _View.__init__(self, request)
        self._validate_api_key()

    def _validate_api_key(self) -> None:
        if not Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.api_key_security'):
            return
        req_key = self.request.headers.get(_SecuredView.USL_API_KEY_HTTP_HEAD)
        key_correct = self._service._api_key_dispatch.validate_key(req_key)
        if not key_correct:
            raise web.HTTPUnauthorized()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmView._app_routes.view("/usl/v1/registerDevice")
class DeviceRegistrationView(_View):
    """
    Device registration view.
    """
    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.UPDATE}})
    async def post(self) -> Dict:

        class MethodSchema(Schema):
            url = fields.URL(required=True)
            pin = fields.Str(required=True)
            s3_account_name = fields.Str(required=True)
            s3_account_email = fields.Email(required=True)
            s3_account_password = fields.Str(required=True)
            iam_user_name = fields.Str(required=True)
            iam_user_password = fields.Str(required=True)
            bucket_name = fields.Str(required=True)

            @validates('pin')
            def validate_pin(self, value: str) -> None:
                if len(value) != 4 or not value.isdecimal():
                    raise ValidationError('Invalid PIN format')

        try:
            body = await self.request.json()
            params = MethodSchema().load(body)
            return await self._service.post_register_device(self._s3_account_service, **params)
        except (JSONDecodeError, ValidationError) as e:
            desc = 'Malformed input payload'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)

    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.LIST}})
    async def get(self) -> None:
        await self._service.get_register_device()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmView._app_routes.view("/usl/v1/registrationToken")
class RegistrationTokenView(_View):
    """
    Registration token generation view.
    """
    @CsmAuth.permissions({Resource.LYVE_PILOT: {Action.LIST}})
    async def get(self) -> Dict[str, str]:
        return await self._service.get_registration_token()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/devices")
class DeviceView(_SecuredView):
    """
    Devices list view.
    """
    async def get(self) -> List[Dict[str, str]]:
        return await self._service.get_device_list()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/devices/{device_id}/volumes")
class DeviceVolumesListView(_SecuredView):
    """
    Volumes list view.
    """
    async def get(self) -> List[Dict[str, Any]]:

        class MethodSchema(Schema):
            device_id = fields.UUID(required=True)

        try:
            params = MethodSchema().load(self.request.match_info)
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        try:
            body = await self.request.json()
            access_params = AccessParamsSchema().load(body)
        except (JSONDecodeError, ValidationError) as e:
            desc = 'Unable to validate payload with access parameters'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        return await self._service.get_device_volumes_list(
            params['device_id'], *AccessParamsSchema.flatten(access_params)
        )


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/devices/{device_id}/volumes/{volume_id}/mount")
class DeviceVolumeMountView(_SecuredView):
    """
    Volume mount view.
    """
    async def post(self) -> Dict[str, str]:

        class MethodSchema(Schema):
            device_id = fields.UUID(required=True)
            volume_id = fields.UUID(required=True)

        try:
            params = MethodSchema().load(self.request.match_info)
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        try:
            body = await self.request.json()
            access_params = AccessParamsSchema().load(body)
        except (JSONDecodeError, ValidationError) as e:
            desc = 'Unable to validate payload with access parameters'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        return await self._service.post_device_volume_mount(
            params['device_id'],
            params['volume_id'],
            *AccessParamsSchema.flatten(access_params),
        )


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/devices/{device_id}/volumes/{volume_id}/umount")
class DeviceVolumeUnmountView(_SecuredView):
    """
    Volume unmount view.
    """
    async def post(self) -> str:

        class MethodSchema(Schema):
            device_id = fields.UUID(required=True)
            volume_id = fields.UUID(required=True)


        class UmountAccessParamsSchema(AccessParamsSchema):
            handle = fields.Str(required=True)


        try:
            params = MethodSchema().load(self.request.match_info)
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        try:
            body = await self.request.json()
            access_params = UmountAccessParamsSchema().load(body)
        except (JSONDecodeError, ValidationError) as e:
            desc = 'Unable to validate payload with access parameters'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        return await self._service.post_device_volume_unmount(
            params['device_id'],
            params['volume_id'],
            *AccessParamsSchema.flatten(access_params),
        )


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/events")
class UdsEventsView(_SecuredView):
    """
    UDS Events view.
    """
    async def get(self) -> str:
        return await self._service.get_events()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/system")
class SystemView(_SecuredView):
    """
    System information view.
    """
    async def get(self) -> Dict[str, str]:
        return await self._service.get_system()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/system/certificates")
class SystemCertificatesView(_SecuredView):
    """
    System certificates view.
    """
    async def post(self) -> web.Response:
        try:
            public_key = await self._service.post_system_certificates()
        except CsmPermissionDenied:
            raise web.HTTPForbidden()
        return web.Response(body=public_key)

    async def put(self) -> None:
        certificate = await self.request.read()
        try:
            await self._service.put_system_certificates(certificate)
        except CsmPermissionDenied:
            raise web.HTTPForbidden()
        raise web.HTTPNoContent()

    async def delete(self) -> None:
        try:
            await self._service.delete_system_certificates()
        except CsmPermissionDenied:
            raise web.HTTPForbidden()
        # Don't return 200 on success, but 204 as USL API specification requires
        raise web.HTTPNoContent()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/system/certificates/{type}")
class SystemCertificatesByTypeView(_SecuredView):
    """
    System certificates view by type.
    """
    async def get(self) -> web.Response:

        class MethodSchema(Schema):
            type = fields.Str(required=True)

            @validates('type')
            def validate_type(self, value: str) -> None:
                valid_values = (
                    'nativeCertificate',
                    'domainCertificate',
                    'nativePrivateKey',
                    'domainPrivateKey',
                )
                if value not in valid_values:
                    raise ValidationError('Invalid certificate type')

        try:
            params = MethodSchema().load(self.request.match_info)
            certificate = await self._service.get_system_certificates_by_type(params['type'])
            return web.Response(body=certificate)
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)
        except CsmNotFoundError:
            raise web.HTTPNotFound()


@Decorators.decorate_if(not Options.debug, _Proxy.on_loopback_only)
@CsmAuth.public
@CsmView._app_routes.view("/usl/v1/system/network/interfaces")
class NetworkInterfacesView(_SecuredView):
    """
    Network interfaces list view.
    """
    async def get(self) -> List[Dict[str, Any]]:
        return await self._service.get_network_interfaces()
