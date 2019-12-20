#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          usl.py
 Description:       A controller for all USL calls.

 Creation Date:     10/21/2019
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from aiohttp import web
from json import JSONDecodeError
from marshmallow import Schema, ValidationError, fields, validates
from typing import Any, Callable, Dict, List, Type

from csm.common.errors import CsmError
from csm.common.log import Log
from csm.core.services.usl import UslService
from .view import CsmAuth

# TODO: make USL views inherit CSM view, handle authorization
@CsmAuth.public
class View(web.View):
    """
    Generic view class for USL API views. Binds a view to an USL service.
    """
    def __init__(self, request: web.Request, usl_service: UslService):
        super().__init__(request)
        self._usl_service = usl_service

    @staticmethod
    def as_generic_view_class(
        f: Callable[['UslController'], Any]
    ) -> Callable[['UslController'], Type[web.View]]:

        def wrapper(self: 'UslController') -> Type[web.View]:
            base: Any = f(self)
            class Child(base):

                def __init__(child_self, request: web.Request) -> None:
                    super().__init__(request, self._usl_service)
            return Child
        return wrapper


class DeviceView(View):
    """
    Devices list and registration view.
    """
    async def get(self) -> List[Dict[str, str]]:
        return await self._usl_service.get_device_list()

    async def post(self) -> None:

        class MethodSchema(Schema):
            url = fields.URL(required=True)
            pin = fields.Str(required=True)

            @validates('pin')
            def validate_pin(self, value: str) -> None:
                if len(value) != 4 or not value.isdecimal():
                    raise ValidationError('Invalid PIN format')

        try:
            body = await self.request.json()
            params = MethodSchema().load(body)
            return await self._usl_service.register_device(params['url'], params['pin'])
        except (JSONDecodeError, ValidationError) as e:
            desc = 'Malformed input payload'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)


class DeviceVolumesListView(View):
    """
    Volumes list view.
    """
    async def get(self) -> List[Dict[str, Any]]:

        class MethodSchema(Schema):
            device_id = fields.UUID(required=True)

        try:
            params = MethodSchema().load(self.request.match_info)
            return await self._usl_service.get_device_volumes_list(params['device_id'])
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)


class DeviceVolumeMountView(View):
    """
    Volume mount view.
    """
    async def post(self) -> Dict[str, str]:

        class MethodSchema(Schema):
            device_id = fields.UUID(required=True)
            volume_id = fields.UUID(required=True)

        try:
            params = MethodSchema().load(self.request.match_info)
            return await self._usl_service.post_device_volume_mount(
                params['device_id'],
                params['volume_id'],
            )
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)


class DeviceVolumeUnmountView(View):
    """
    Volume unmount view.
    """
    async def post(self) -> str:

        class MethodSchema(Schema):
            device_id = fields.UUID(required=True)
            volume_id = fields.UUID(required=True)

        try:
            params = MethodSchema().load(self.request.match_info)
            return await self._usl_service.post_device_volume_unmount(
                params['device_id'],
                params['volume_id'],
            )
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)


class RegistrationTokenView(View):
    """
    Registration token generation view.
    """
    async def get(self) -> Dict[str, str]:
        return await self._usl_service.get_registration_token()


class SystemView(View):
    """
    System information view.
    """
    async def get(self) -> Dict[str, str]:
        return await self._usl_service.get_system()


class SystemCertificatesView(View):
    """
    System certificates view.
    """
    async def delete(self) -> None:
        return await self._usl_service.delete_system_certificates()


class SystemCertificatesByTypeView(View):
    """
    System certificates view by type.
    """
    async def get(self) -> bytes:

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
            return await self._usl_service.get_system_certificates_by_type(params['type'])
        except ValidationError as e:
            desc = 'Malformed path'
            Log.error(f'{desc}: {e}')
            raise CsmError(desc=desc)


class NetworkInterfacesView(View):
    """
    Network interfaces list view.
    """
    async def get(self) -> List[Dict[str, Any]]:
        return await self._usl_service.get_network_interfaces()


class UslController:
    """
    Exposes configured USL API views for consumption by the routing module.
    """
    def __init__(self, usl_service: UslService) -> None:
        self._usl_service = usl_service

    @View.as_generic_view_class
    def get_device_view_class(self) -> Type[DeviceView]:
        return DeviceView

    @View.as_generic_view_class
    def get_device_volumes_list_view_class(self) -> Type[DeviceVolumesListView]:
        return DeviceVolumesListView

    @View.as_generic_view_class
    def get_device_volume_mount_view_class(self) -> Type[DeviceVolumeMountView]:
        return DeviceVolumeMountView

    @View.as_generic_view_class
    def get_device_volume_unmount_view_class(self) -> Type[DeviceVolumeUnmountView]:
        return DeviceVolumeUnmountView

    @View.as_generic_view_class
    def get_registration_token_view_class(self) -> Type[RegistrationTokenView]:
        return RegistrationTokenView

    @View.as_generic_view_class
    def get_system_view_class(self) -> Type[SystemView]:
        return SystemView

    @View.as_generic_view_class
    def get_system_certificates_view_class(self) -> Type[SystemCertificatesView]:
        return SystemCertificatesView

    @View.as_generic_view_class
    def get_system_certificates_by_type_view_class(self) -> Type[SystemCertificatesByTypeView]:
        return SystemCertificatesByTypeView

    @View.as_generic_view_class
    def get_network_interfaces_view_class(self) -> Type[NetworkInterfacesView]:
        return NetworkInterfacesView
