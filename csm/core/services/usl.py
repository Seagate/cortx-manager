#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          usl.py
 Description:       Services for USL calls

 Creation Date:     10/21/2019
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from aiohttp import web, ClientSession
from random import SystemRandom
from marshmallow import ValidationError
from marshmallow.validate import URL
from typing import Any, Dict, List
from uuid import UUID, uuid4, uuid5
import asyncio
import time
import toml

from csm.common.conf import Conf
from csm.common.errors import CsmError, CsmInternalError, CsmNotFoundError
from csm.common.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.data.models.s3 import S3ConnectionConfig
from csm.core.blogic.models.usl import Device, Volume, MountResponse

DEFAULT_EOS_DEVICE_NAME = 'cloudstore'
DEFAULT_EOS_DEVICE_VENDOR = 'Seagate'

class UslService(ApplicationService):
    """
    Implements USL service operations.
    """
    # FIXME improve token management
    _token: str
    _fake_system_serial_number: str
    _s3cli: Any
    _device: Device
    _volumes: Dict[str, Dict[str, Any]]

    def __init__(self, s3_plugin) -> None:
        """
        Constructor.
        """
        self._token = ''
        self._fake_system_serial_number = 'EES%012d' % time.time()
        self._s3cli = self._create_s3cli(s3_plugin)
        self._device = Device(DEFAULT_EOS_DEVICE_NAME, '0000', self._fake_system_serial_number,
            'internal', self._get_device_uuid(), DEFAULT_EOS_DEVICE_VENDOR)
        self._volumes = {}
        self._buckets = {}

    # TODO: pass S3 server credentials to the server instead of reading from a file
    def _create_s3cli(self, s3_plugin):
        """Creates the S3 client for USL service"""

        s3_conf = S3ConnectionConfig()
        s3_conf.host = Conf.get(const.CSM_GLOBAL_INDEX, 'S3.host')
        s3_conf.port = Conf.get(const.CSM_GLOBAL_INDEX, 'S3.s3_port')

        toml_conf = toml.load(const.USL_S3_CONF)
        return s3_plugin.get_s3_client(toml_conf['credentials']['access_key_id'],
                                       toml_conf['credentials']['secret_key'],
                                       s3_conf)

    def _get_device_uuid(self) -> UUID:
        """Obtains the EOS device UUID from config."""

        return UUID(Conf.get(const.CSM_GLOBAL_INDEX, "PRODUCT.uuid")) or uuid4()

    def _get_volume_uuid(self, bucket_name: str) -> UUID:
        """Generates the EOS volume (bucket) UUID from EOS device UUID and bucket name."""

        return uuid5(self._device.uuid, bucket_name)

    async def _is_bucket_udx_enabled(self, bucket):
        """
        Checks if bucket is UDX enabled

        The UDX enabled bucket contains tag {Key=udx,Value=enabled}
        """

        tags = await self._s3cli.get_bucket_tagging(bucket)
        return tags.get('udx', 'disabled') == 'enabled'

    async def _update_volumes_cache(self):
        """
        Updates the internal buckets cache.

        Obtains the fresh buckets list from S3 server and updates cache with it.
        Keeps cache the same if the server is not available.
        """

        try:
            fresh_buckets = [b.name for b in await self._s3cli.get_all_buckets()
                             if await self._is_bucket_udx_enabled(b)]
            cached_buckets = [v['bucketName'] for _,v in self._volumes.items()]

            # Remove staled volumes
            self._volumes = {k:v for k,v in self._volumes.items()
                             if v['bucketName'] in fresh_buckets}
            # Add new volumes
            for b in fresh_buckets:
                if not b in cached_buckets:
                    volume_uuid = self._get_volume_uuid(b)
                    self._volumes[volume_uuid] = {'bucketName' : b,
                                                  'volume' : Volume(self._device.uuid, 's3', 0, 0,
                                                                    volume_uuid)}
        except Exception as e:
            raise CsmInternalError(desc=f'Unable to update buckets cache: {str(e)}')


    async def get_device_list(self) -> List[Dict[str, str]]:
        """
        Provides a list with all available devices.

        :return: A list with dictionaries, each containing information about a specific device.
        """
        return [vars(self._device)]

    async def get_device_volumes_list(self, device_id: UUID) -> List[Dict[str, Any]]:
        """
        Provides a list of all volumes associated to a specific device.

        :param device_id: Device UUID
        :return: A list with dictionaries, each containing information about a specific volume.
        """

        if device_id != self._device.uuid:
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')
        await self._update_volumes_cache()
        return [vars(v['volume']) for uuid,v in self._volumes.items()]

    async def post_device_volume_mount(self, device_id: UUID, volume_id: UUID) -> Dict[str, str]:
        """
        Attaches a volume associated to a specific device to a mount point.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :return: A dictionary containing the mount handle and the mount path.
        """
        if device_id != self._device.uuid:
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')

        if not volume_id in self._volumes:
            await self._update_volumes_cache()
            if not volume_id in self._volumes:
                raise CsmNotFoundError(desc=f'Volume {volume_id} is not found')
        return vars(MountResponse('handle', '/mnt', self._volumes[volume_id]['bucketName']))

    # TODO replace stub
    async def post_device_volume_unmount(self, device_id: UUID, volume_id: UUID) -> str:
        """
        Detaches a volume associated to a specific device from its current mount point.

        The current implementation reflects the API specification but does nothing.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :return: The volume's mount handle
        """
        return 'handle'

    async def register_device(self, url: str, pin: str) -> None:
        """
        Executes device registration sequence. Communicates with the UDS server in order to start
        registration and verify its status.

        :param url: Registration URL as provided by the UDX portal
        :param pin: Registration PIN as provided by the UDX portal
        """
        uds_url = Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.url') or const.UDS_SERVER_DEFAULT_BASE_URL
        try:
            validate_url = URL(schemes=('http', 'https'))
            validate_url(uds_url)
        except ValidationError:
            reason = 'UDS base URL is not valid'
            Log.error(reason)
            raise web.HTTPInternalServerError(reason=reason)
        endpoint_url = str(uds_url) + '/uds/v1/registration/RegisterDevice'
        # TODO use a single client session object; manage life cycle correctly
        async with ClientSession() as session:
            params = {'url': url, 'regPin': pin, 'regToken': self._token}
            Log.info(f'Start device registration at {uds_url}')
            async with session.put(endpoint_url, params=params) as response:
                if response.status != 201:
                    reason = 'Could not start device registration'
                    Log.error(f'{reason}---unexpected status code {response.status}')
                    raise web.HTTPInternalServerError(reason=reason)
            Log.info('Device registration in process---waiting for confirmation')
            timeout_limit = time.time() + 60
            while time.time() < timeout_limit:
                async with session.get(endpoint_url) as response:
                    if response.status == 200:
                        Log.info('Device registration successful')
                        return
                    elif response.status != 201:
                        reason = 'Device registration failed'
                        Log.error(f'{reason}---unexpected status code {response.status}')
                        raise web.HTTPInternalServerError(reason=reason)
                await asyncio.sleep(1)
            else:
                reason = 'Could not confirm device registration status'
                Log.error(reason)
                raise web.HTTPGatewayTimeout(reason=reason)

    # TODO replace stub
    async def get_registration_token(self) -> Dict[str, str]:
        """
        Generates a random registration token.

        :return: A 12-digit token.
        """
        self._token = ''.join(SystemRandom().sample('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 12))
        return {'registrationToken': self._token}

    # TODO replace stub
    async def get_system(self) -> Dict[str, str]:
        """
        Provides information about the system.

        :return: A dictionary containing system information.
        """
        return {
            'model': 'EES',
            'type': 'ees',
            'serialNumber': self._fake_system_serial_number,
            'friendlyName': 'EESFakeSystem',
            'firmwareVersion': '0.00',
        }

    # TODO replace stub
    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """
        Provides a list of all network interfaces in a system.

        :return: A list containing dictionaries, each containing information about a specific
            network interface.
        """
        return [
            {
                'name': 'tbd',
                'type': 'tbd',
                'macAddress': 'AA:BB:CC:DD:EE:FF',
                'isActive': True,
                'isLoopback': False,
                'ipv4': '127.0.0.1',
                'netmask': '255.0.0.0',
                'broadcast': '127.255.255.255',
                'gateway': '127.255.255.254',
                'ipv6': '::1',
                'link': 'tbd',
                'duplex': 'tbd',
                'speed': 0,
            }
        ]
