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
from csm.common.errors import CsmInternalError, CsmNotFoundError
from csm.common.key_manager import KeyManager
from csm.common.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.data.access import Query
from csm.core.data.access.filters import Compare
from csm.core.data.db.db_provider import DataBaseProvider
from csm.core.data.models.s3 import S3ConnectionConfig, IamError
from csm.core.data.models.usl import (Device, Volume, NewVolumeEvent, VolumeRemovedEvent,
                                      MountResponse)
from csm.core.services.s3.utils import CsmS3ConfigurationFactory, IamRootClient

DEFAULT_EOS_DEVICE_VENDOR = 'Seagate'
DEFAULT_VOLUME_CACHE_UPDATE_PERIOD = 3


class UslService(ApplicationService):
    """
    Implements USL service operations.
    """
    # FIXME improve token management
    _token: str
    _s3plugin: Any
    _s3cli: Any
    _iamcli: Any
    _storage: DataBaseProvider
    _device: Device
    _volumes: Dict[UUID, Volume]
    _volumes_sustaining_task: asyncio.Task
    _event_queue: asyncio.Queue

    def __init__(self, s3_plugin, storage) -> None:
        """
        Constructor.
        """
        loop = asyncio.get_event_loop()

        self._token = ''
        self._s3plugin = s3_plugin
        self._s3cli = self._create_s3cli(s3_plugin)
        self._iamcli = IamRootClient()
        dev_uuid = self._get_device_uuid()
        self._device = Device.instantiate(
            self._get_system_friendly_name(),
            '0000',
            str(dev_uuid),
            'S3',
            dev_uuid,
            DEFAULT_EOS_DEVICE_VENDOR,
        )
        self._storage = storage
        self._event_queue = asyncio.Queue(0, loop=loop)
        self._volumes = loop.run_until_complete(self._restore_volume_cache())
        self._volumes_sustaining_task = loop.create_task(self._sustain_cache())

    # TODO: pass S3 server credentials to the server instead of reading from a file
    def _create_s3cli(self, s3_plugin):
        """Creates the S3 client for USL service"""

        s3_conf = S3ConnectionConfig()
        s3_conf.host = Conf.get(const.CSM_GLOBAL_INDEX, 'S3.host')
        s3_conf.port = Conf.get(const.CSM_GLOBAL_INDEX, 'S3.s3_port')

        usl_s3_conf = toml.load(const.USL_S3_CONF)
        return s3_plugin.get_s3_client(usl_s3_conf['credentials']['access_key_id'],
                                       usl_s3_conf['credentials']['secret_key'],
                                       s3_conf)

    async def _restore_volume_cache(self) -> Dict[UUID, Volume]:
        """Restores the volume cache from Consul KVS"""

        try:
            cache = {volume.uuid: volume
                     for volume in await self._storage(Volume).get(Query())}
        except Exception as e:
            reason = (f"Failed to restore USL volume cache from Consul KVS: {str(e)}\n"
                      f"All volumes are considered new. Redundant events may appear")
            Log.error(reason)
            cache = {}
        return cache

    def _get_system_friendly_name(self) -> str:
        return str(Conf.get(const.CSM_GLOBAL_INDEX, 'PRODUCT.friendly_name') or 'local')

    def _get_device_uuid(self) -> UUID:
        """Obtains the EOS device UUID from config."""

        return UUID(Conf.get(const.CSM_GLOBAL_INDEX, "PRODUCT.uuid")) or uuid4()

    def _get_volume_name(self, bucket_name: str) -> UUID:
        return self._get_system_friendly_name() + ": " + bucket_name

    def _get_volume_uuid(self, bucket_name: str) -> UUID:
        """Generates the EOS volume (bucket) UUID from EOS device UUID and bucket name."""

        return uuid5(self._device.uuid, bucket_name)

    async def _create_udx_account(self, account_name, account_email, account_password, bucket_name):
        """
        Creates an UDX account with dedicated bucket.
        """

        Log.debug(f'Creating UDX S3 account. account_name: {account_name}')
        account = await self._iamcli.create_account(account_name, account_email)
        if isinstance(account, IamError):
            raise CsmInternalError(f'Failed to create UDX S3 account {account.error_code}: '
                                   f'{account.error_message}')

        iam_conf = CsmS3ConfigurationFactory.get_iam_connection_config()
        account_client = self._s3plugin.get_iam_client(account.access_key_id, account.secret_key_id,
                                                       iam_conf)

        try:
            await self._create_udx_bucket(account, bucket_name)
            Log.debug(f"Creating Login profile for account: {account}")
            profile = await account_client.create_account_login_profile(account_name,
                                                                        account_password)
            if isinstance(profile, IamError):
                raise CsmInternalError("Failed to create loging profile for UDX S3 account")
        except Exception as e:
            await account_client.delete_account(account.account_name)
            raise e

        return {
            "account_name": account.account_name,
            "account_email": account.account_email,
            "access_key": account.access_key_id,
            "secret_key": account.secret_key_id,
            "bucket_name": bucket_name,
        }

    async def _create_udx_bucket(self, account, bucket_name):
        Log.debug(f'Creating UDX bucket {bucket_name} for s3 account: {account.account_name}')
        postfixed_bucket_name = bucket_name + '-udx'
        bucket_tags = {"udx": "enabled"}

        try:
            conn_conf = CsmS3ConfigurationFactory.get_s3_connection_config()
            s3_client = self._s3plugin.get_s3_client(account.access_key_id, account.secret_key_id,
                                                     conn_conf)
            await s3_client.create_bucket(postfixed_bucket_name)
            Log.info(f'UDX bucket {postfixed_bucket_name} is created')
            await s3_client.put_bucket_tagging(postfixed_bucket_name, bucket_tags)
            Log.info(f'UDX bucket {postfixed_bucket_name} is taggged with {bucket_tags}')
        except Exception as e:
            raise CsmInternalError(f'UDX bucket creation failed: {str(e)}')

    async def _is_bucket_udx_enabled(self, bucket):
        """
        Checks if bucket is UDX enabled

        The UDX enabled bucket contains tag {Key=udx,Value=enabled}
        """

        tags = await self._s3cli.get_bucket_tagging(bucket)
        return tags.get('udx', 'disabled') == 'enabled'

    async def _sustain_cache(self):
        """The infinite asynchronous task that sustains volumes cache"""

        volume_cache_update_period = float(
            Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.volume_cache_update_period_seconds') or
            DEFAULT_VOLUME_CACHE_UPDATE_PERIOD
        )

        while True:
            await asyncio.sleep(volume_cache_update_period)
            try:
                await self._update_volumes_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                reason = "Unpredictable exception during volume cache update" + str(e)
                # Do not fail here, keep trying to update the cache
                Log.error(reason)

    async def _get_volume_cache(self) -> Dict[UUID, Volume]:
        """
        Creates the internal volumes cache from buckets list retrieved from S3 server
        """
        volumes = {}
        for b in await self._s3cli.get_all_buckets():
            if await self._is_bucket_udx_enabled(b):
                volume_uuid = self._get_volume_uuid(b.name)
                volumes[volume_uuid] = Volume.instantiate(self._get_volume_name(b.name), b.name,
                                                          self._device.uuid, volume_uuid)
        return volumes

    async def _update_volumes_cache(self):
        """
        Updates the internal buckets cache.

        Obtains the fresh buckets list from S3 server and updates cache with it.
        Keeps cache the same if the server is not available.
        """
        fresh_cache = await self._get_volume_cache()

        new_volume_uuids = fresh_cache.keys() - self._volumes.keys()
        volume_removed_uuids = self._volumes.keys() - fresh_cache.keys()

        for uuid in new_volume_uuids:
            e = NewVolumeEvent.instantiate(fresh_cache[uuid])
            await self._event_queue.put(e)

        for uuid in volume_removed_uuids:
            e = VolumeRemovedEvent.instantiate(uuid)
            await self._event_queue.put(e)

        self._volumes = fresh_cache

    async def get_device_list(self) -> List[Dict[str, str]]:
        """
        Provides a list with all available devices.

        :return: A list with dictionaries, each containing information about a specific device.
        """
        return [self._device.to_primitive()]

    async def get_device_volumes_list(self, device_id: UUID) -> List[Dict[str, Any]]:
        """
        Provides a list of all volumes associated to a specific device.

        :param device_id: Device UUID
        :return: A list with dictionaries, each containing information about a specific volume.
        """

        if device_id != self._device.uuid:
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')
        return [v.to_primitive(role='public') for uuid, v in self._volumes.items()]

    async def post_device_volume_mount(self, device_id: UUID, volume_id: UUID) -> Dict[str, str]:
        """
        Attaches a volume associated to a specific device to a mount point.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :return: A dictionary containing the mount handle and the mount path.
        """
        if device_id != self._device.uuid:
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')

        if volume_id not in self._volumes:
            raise CsmNotFoundError(desc=f'Volume {volume_id} is not found')
        return MountResponse.instantiate(self._volumes[volume_id].bucketName,
                                         self._volumes[volume_id].bucketName).to_primitive()

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

    async def get_events(self) -> str:
        """
        Returns USL events one-by-one
        """
        e = await self._event_queue.get()
        if isinstance(e, NewVolumeEvent):
            await self._storage(Volume).store(e.volume)
        elif isinstance(e, VolumeRemovedEvent):
            await self._storage(Volume).delete(Compare(Volume.uuid, '=', e.uuid))
        else:
            raise CsmInternalError("Unknown entry in USL events queue")
        return e.to_primitive(role='public')

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
                        KeyManager.create_security_material(const.UDS_CERTIFICATES_PATH,
                                                            const.UDS_DOMAIN_CERTIFICATE_FILENAME)
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
        friendly_name = self._get_system_friendly_name()
        return {
            'model': 'EES',
            'type': 'ees',
            'serialNumber': self._device.uuid,
            'friendlyName': friendly_name,
            'firmwareVersion': '0.00',
        }

    # TODO replace stub
    async def delete_system_certificates(self) -> None:
        try:
            path = KeyManager.get_security_material(const.UDS_CERTIFICATES_PATH,
                                                    const.UDS_DOMAIN_CERTIFICATE_FILENAME)
            path.unlink()
        except FileNotFoundError:
            raise web.HTTPForbidden()
        # Don't return 200 on success, but 204 as USL API specification requires
        raise web.HTTPNoContent()

    # TODO replace stub
    async def get_system_certificates_by_type(self, certificate_type: str) -> bytes:
        """
        Provides one of the available system certificates according to the specified type.

        :param certificate_type: Certificate type
        :return: The corresponding system certificate
        """
        if certificate_type != 'domainCertificate':
            raise web.HTTPNotImplemented()

        try:
            cert = KeyManager.get_security_material(const.UDS_CERTIFICATES_PATH,
                                                    const.UDS_DOMAIN_CERTIFICATE_FILENAME)
            with cert.open('rb') as f:
                return f.read()
        except FileNotFoundError:
            raise web.HTTPNotFound()

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
