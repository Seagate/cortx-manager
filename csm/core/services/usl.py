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
import time

from aiohttp import ClientSession, TCPConnector
from aiohttp import ClientError as HttpClientError
from boto.s3.bucket import Bucket
from random import SystemRandom
from marshmallow import ValidationError
from marshmallow.validate import URL
from typing import Any, Dict, List
from uuid import UUID, uuid4, uuid5

from csm.common.conf import Conf
from csm.common.errors import (
    CsmGatewayTimeout, CsmInternalError, CsmNotFoundError, CsmPermissionDenied, InvalidRequest)
from csm.common.periodic import Periodic
from cortx.utils.data.access import Query
from cortx.utils.log import Log
from csm.common.runtime import Options
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.services.storage_capacity import StorageCapacityService
from csm.core.data.models.system_config import ApplianceName
from csm.core.data.models.usl import Device, Volume, ApiKey
from csm.core.services.s3.utils import CsmS3ConfigurationFactory
from csm.core.services.usl_net_ifaces import get_interface_details
from csm.core.services.usl_certificate_manager import (
    USLDomainCertificateManager, USLNativeCertificateManager, CertificateError
)
from csm.core.services.usl_s3 import UslS3BucketsController
from csm.plugins.cortx.provisioner import NetworkConfigFetchError
from cortx.utils.security.secure_storage import SecureStorage
from cortx.utils.security.cipher import Cipher


DEFAULT_CORTX_DEVICE_VENDOR = 'Seagate'
USL_API_KEY_UPDATE_PERIOD = 24 * 60 * 60


class UslApiKeyDispatcher:
    def __init__(self, storage):
        self._key = None
        self._storage = storage
        self._updater = Periodic(USL_API_KEY_UPDATE_PERIOD, self._update_key)
        self._updater.start()

    async def _update_key(self) -> None:
        new_key = uuid4()
        key_model = ApiKey.instantiate(new_key)
        await self._storage(ApiKey).store(key_model)
        self._key = str(new_key)
        Log.info(f'Current USL API key is {self._key}')

    def validate_key(self, request_key: str) -> bool:
        return self._key == request_key


class UslService(ApplicationService):
    """
    Implements USL service operations.
    """
    # FIXME improve token management
    _s3plugin: Any
    _domain_certificate_manager: USLDomainCertificateManager
    _native_certificate_manager: USLNativeCertificateManager
    _api_key_dispatch: UslApiKeyDispatcher

    def __init__(self, s3_plugin, storage, provisioner) -> None:
        """
        Constructor.
        """
        self._s3plugin = s3_plugin
        self._provisioner = provisioner
        self._storage = storage
        self._device_uuid = self._get_device_uuid()
        key = Cipher.generate_key(str(self._device_uuid), 'USL')
        secure_storage = SecureStorage(self._storage, key)
        self._domain_certificate_manager = USLDomainCertificateManager(secure_storage)
        self._native_certificate_manager = USLNativeCertificateManager()
        self._api_key_dispatch = UslApiKeyDispatcher(self._storage)

    async def _get_system_friendly_name(self) -> str:
        entries = await self._storage(ApplianceName).get(Query())
        appliance_name = next(iter(entries), None)
        if appliance_name is None:
            reason = 'Could not retrieve friendly name from storage'
            Log.error(f'{reason}')
            raise CsmInternalError(desc=reason)
        return str(appliance_name)

    def _get_device_uuid(self) -> UUID:
        """

        Returns the CORTX cluster ID as in CSM configuration file.
        """
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, 'PROVISIONER.cluster_id')
        if Options.debug and cluster_id is None:
            cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, 'DEBUG.default_cluster_id')
        device_uuid = cluster_id
        if device_uuid is None:
            reason = 'Could not obtain cluster ID from CSM configuration file'
            Log.error(f'{reason}')
            raise CsmInternalError(desc=reason)
        return UUID(device_uuid)

    async def _is_bucket_lyve_pilot_enabled(self, s3_cli, bucket):
        """
        Checks if bucket is enabled for Lyve Pilot

        Buckets enabled for Lyve Pilot contain tag {Key=udx,Value=enabled}
        """

        tags = await s3_cli.get_bucket_tagging(bucket.name)
        return tags.get('udx', 'disabled') == 'enabled'

    async def _get_volume_name(self, bucket_name: str) -> str:
        return await self._get_system_friendly_name() + ": " + bucket_name

    def _get_volume_uuid(self, bucket_name: str) -> UUID:
        """Generates the CORTX volume (bucket) UUID from CORTX device UUID and bucket name."""
        return uuid5(self._device_uuid, bucket_name)

    async def _format_bucket_as_volume(self, bucket: Bucket) -> Volume:
        bucket_name = bucket.name
        volume_name = await self._get_volume_name(bucket_name)
        device_uuid = self._device_uuid
        volume_uuid = self._get_volume_uuid(bucket_name)
        capacity_details = await StorageCapacityService(self._provisioner).get_capacity_details()
        capacity_size = capacity_details[const.SIZE]
        capacity_used = capacity_details[const.USED]
        return Volume.instantiate(
            volume_name, bucket_name, device_uuid, volume_uuid, capacity_size, capacity_used)

    async def _get_lyve_pilot_volume_list(
        self, access_key_id: str, secret_access_key: str
    ) -> Dict[UUID, Volume]:
        s3_client = self._s3plugin.get_s3_client(
            access_key_id, secret_access_key, CsmS3ConfigurationFactory.get_s3_connection_config()
        )
        volumes = {}
        for bucket in await s3_client.get_all_buckets():
            if not await self._is_bucket_lyve_pilot_enabled(s3_client, bucket):
                continue
            volume = await self._format_bucket_as_volume(bucket)
            volumes[volume.uuid] = volume
        return volumes

    # TODO replace stub
    async def _format_device_info(self) -> Device:
        device_uuid = self._device_uuid
        return Device.instantiate(
            await self._get_system_friendly_name(),
            '0000',
            str(device_uuid),
            'S3',
            device_uuid,
            DEFAULT_CORTX_DEVICE_VENDOR,
        )

    async def get_device_list(self) -> List[Dict[str, str]]:
        """
        Provides a list with all available devices.

        :return: A list with dictionaries, each containing information about a specific device.
        """
        device = await self._format_device_info()
        return [device.to_primitive()]

    async def get_device_volumes_list(
        self, device_id: UUID, uri: str, access_key_id: str, secret_access_key: str
    ) -> List[Dict[str, Any]]:
        """
        Provides a list of all volumes associated to a specific device.

        :param device_id: Device UUID
        :param uri: URI to storage service
        :param access_key_id: Access key ID to storage service
        :param secret_access_key: Secret access key to storage service
        :return: A list with dictionaries, each containing information about a specific volume.
        """
        if device_id != self._device_uuid:
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')
        volumes = await self._get_lyve_pilot_volume_list(access_key_id, secret_access_key)
        return [v.to_primitive(role='public') for _, v in volumes.items()]

    async def _build_lyve_pilot_volume_mount_info(
        self, device_id: UUID, volume_id: UUID, access_key_id: str, secret_access_key: str
    ) -> Dict[str, str]:
        """
        Compute Lyve Pilot mount info if device and volume with specified IDs exist.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :param access_key_id: Access key ID to storage service
        :param secret_access_key: Secret access key to storage service
        :return: A dictionary containing the mount handle and the mount path.
        """
        if device_id != self._device_uuid:
            raise CsmNotFoundError(desc=f'Device {device_id} not found')
        volumes = await self._get_lyve_pilot_volume_list(access_key_id, secret_access_key)
        if volume_id not in volumes:
            raise CsmNotFoundError(desc=f'Volume {volume_id} not found on device {device_id}')
        return {
            'mountPath': volumes[volume_id].bucketName,
            'handle': volumes[volume_id].bucketName
        }

    async def post_device_volume_mount(
        self, device_id: UUID, volume_id: UUID, uri: str, access_key_id: str, secret_access_key: str
    ) -> Dict[str, str]:
        """
        Attaches a volume associated to a specific device to a mount point.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :param uri: URI to storage service
        :param access_key_id: Access key ID to storage service
        :param secret_access_key: Secret access key to storage service
        :return: A dictionary containing the mount handle and the mount path.
        """
        return await self._build_lyve_pilot_volume_mount_info(
            device_id, volume_id, access_key_id, secret_access_key)

    async def post_device_volume_unmount(
        self, device_id: UUID, volume_id: UUID, uri: str, access_key_id: str, secret_access_key: str
    ) -> str:
        """
        Detaches a volume associated to a specific device from its current mount point.

        The current implementation reflects the API specification but does nothing.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :param uri: URI to storage service
        :param access_key_id: Access key ID to storage service
        :param secret_access_key: Secret access key to storage service
        :return: The volume's mount handle
        """
        mount_info = await self._build_lyve_pilot_volume_mount_info(
            device_id, volume_id, access_key_id, secret_access_key)
        return mount_info['handle']

    async def get_events(self) -> None:
        """
        Returns USL events one-by-one
        """
        # TODO implement
        pass

    async def _register_device(self, registration_info: Dict) -> None:
        """
        Executes device registration sequence. Communicates with the UDS server in order to start
        registration and verify its status.

        :param registration_info: UDS registration info
        """
        uds_url = Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.url') or const.UDS_SERVER_DEFAULT_BASE_URL
        try:
            validate_url = URL(schemes=('http', 'https'))
            validate_url(uds_url)
        except ValidationError:
            reason = 'UDS base URL is not valid'
            Log.error(reason)
            raise CsmInternalError(desc=reason)
        # TODO validate registration body
        endpoint_url = str(uds_url) + '/uds/v1/registration/RegisterDevice'
        # FIXME add relevant certificates to SSL context instead of disabling validation
        async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
            Log.info(f'Start device registration at {uds_url}')
            async with session.put(endpoint_url, json=registration_info) as response:
                if response.status != 201:
                    reason = 'Could not start device registration'
                    Log.error(f'{reason}---unexpected status code {response.status}')
                    raise CsmInternalError(desc=reason)
            Log.info('Device registration in process---waiting for confirmation')
            timeout_limit = time.time() + 60
            while time.time() < timeout_limit:
                try:
                    async with session.get(endpoint_url) as response:
                        if response.status == 200:
                            Log.info('Device registration successful')
                            break
                        elif response.status == 203:
                            reason = 'Registration PIN is required; please retry'
                            Log.error(reason)
                            raise InvalidRequest(reason)
                        elif response.status != 201:
                            reason = 'Lyve Pilot failed to register the device'
                            Log.error(f'{reason}---unexpected status code {response.status}')
                            raise CsmInternalError(desc=reason)
                except HttpClientError as e:
                    reason = 'HTTP client error suppressed during registration confirmation'
                    Log.warn(f'{reason}---{str(e)}')
                await asyncio.sleep(1)
            else:
                reason = 'Could not confirm device registration status'
                Log.error(reason)
                raise CsmGatewayTimeout(desc=reason)

    async def post_register_device(self, s3_buckets_service, registration_info: Dict) -> None:
        account_name = registration_info['accessParams']['accountName']
        credentials = registration_info['accessParams']['credentials']
        access_key = credentials['accessKey']
        secret_access_key = credentials['secretKey']
        buckets_controller = UslS3BucketsController(
            s3_buckets_service, account_name, access_key, secret_access_key)
        bucket_name = registration_info['internalCortxParams']['bucketName']
        await buckets_controller.enable_lyve_pilot(bucket_name)
        try:
            uds_registration_info = registration_info.copy()
            del uds_registration_info['internalCortxParams']
            await self._register_device(uds_registration_info)
        except Exception as e:
            await buckets_controller.disable_lyve_pilot(bucket_name)
            raise e

    async def get_register_device(self) -> None:
        uds_url = Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.url') or const.UDS_SERVER_DEFAULT_BASE_URL
        endpoint_url = str(uds_url) + '/uds/v1/registration/RegisterDevice'
        # FIXME add relevant certificates to SSL context instead of disabling validation
        async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
            async with session.get(endpoint_url) as response:
                if response.status != 200:
                    raise CsmNotFoundError()

    # TODO replace stub
    async def get_registration_token(self) -> Dict[str, str]:
        """
        Generates a random registration token.

        :return: A 12-digit token.
        """
        token = ''.join(SystemRandom().sample('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 12))
        return {'registrationToken': token}

    async def _get_mgmt_url(self) -> Dict[str, str]:
        """
        Returns a management link to be provided to the UDS.

        :return: a dictionary with a management link's name and value.
        """
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE.CSM_WEB.ssl_check')
        network_configuration = await self._provisioner.get_network_configuration()
        port = \
            Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE.CSM_WEB.port') or const.WEB_DEFAULT_PORT
        scheme = 'https' if ssl_check else 'http'
        host = f'{network_configuration.mgmt_vip}'
        url = scheme + '://' + host + ':' + str(port)
        mgmt_url = {
            'name': 'mgmtUrl',
            'url': url,
        }
        return mgmt_url

    async def _get_service_urls(self) -> List[Dict[str, str]]:
        """
        Gathers all service URLs to be provided to the UDS.

        :return: a list of service URLs.
        """

        service_urls = []
        mgmt_url = await self._get_mgmt_url()
        service_urls.append(mgmt_url)
        return service_urls

    # TODO replace stub
    async def get_system(self) -> Dict[str, Any]:
        """
        Provides information about the system.

        :return: A dictionary containing system information.
        """
        friendly_name = await self._get_system_friendly_name()
        service_urls = await self._get_service_urls()
        return {
            'model': 'CORTX',
            'type': 'ees',
            'serialNumber': str(self._device_uuid),
            'friendlyName': friendly_name,
            'firmwareVersion': '0.00',
            'serviceUrls': service_urls,
        }

    async def post_system_certificates(self) -> bytes:
        """
        Create USL domain key pair in case it does not exist.

        :returns: USL public key as raw bytes
        """
        if await self._domain_certificate_manager.get_private_key_bytes() is not None:
            reason = 'Domain certificate already exists'
            raise CsmPermissionDenied(reason)
        await self._domain_certificate_manager.create_private_key_file(overwrite=False)
        private_key_bytes = await self._domain_certificate_manager.get_private_key_bytes()
        if private_key_bytes is None:
            reason = 'Could not read USL private key'
            Log.error(reason)
            raise CsmInternalError(reason)
        public_key = await self._domain_certificate_manager.get_public_key_bytes()
        if public_key is None:
            reason = 'Could not read USL public key'
            Log.error(f'{reason}')
            raise CsmInternalError(reason)
        return public_key

    async def put_system_certificates(self, certificate: bytes) -> None:
        if await self._domain_certificate_manager.get_certificate_bytes() is not None:
            reason = 'Domain certificate already exists'
            raise CsmPermissionDenied(reason)
        try:
            await self._domain_certificate_manager.create_certificate_file(certificate)
        except CertificateError as e:
            reason = 'Could not update USL certificate'
            Log.error(f'{reason}: {e}')
            raise CsmInternalError(reason)

    async def delete_system_certificates(self) -> None:
        """
        Delete all key material related with the USL domain certificate.
        """

        deleted = await self._domain_certificate_manager.delete_key_material()
        if not deleted:
            reason = 'Failed to delete the domain certificate'
            raise CsmPermissionDenied(reason)

    async def get_system_certificates_by_type(self, material_type: str) -> bytes:
        """
        Provides key material according to the specified type.

        :param material_type: Key material type
        :return: The corresponding key material as raw bytes
        """
        get_material_bytes = {
            'domainCertificate': self._domain_certificate_manager.get_certificate_bytes,
            'domainPrivateKey': self._domain_certificate_manager.get_private_key_bytes,
            'nativeCertificate': self._native_certificate_manager.get_certificate_bytes,
            'nativePrivateKey': self._native_certificate_manager.get_private_key_bytes,
        }.get(material_type)
        if get_material_bytes is None:
            reason = f'Unexpected key material type "{material_type}"'
            Log.error(reason)
            raise CsmInternalError(reason)
        material = await get_material_bytes()
        if material is None:
            reason = f'Key material type "{material_type}" is not found'
            raise CsmNotFoundError(reason)
        return material

    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """
        Provides a list of all network interfaces in a system.

        :return: A list containing dictionaries, each containing information about a specific
            network interface.
        """
        try:
            conf = await self._provisioner.get_network_configuration()
            ip = conf.cluster_ip
        except NetworkConfigFetchError as e:
            reason = 'Could not obtain network configuration from provisioner'
            Log.error(f'{reason}: {e}')
            raise CsmInternalError(reason) from e
        try:
            iface_data = get_interface_details(ip)
        except (ValueError, RuntimeError) as e:
            reason = f'Could not obtain interface details from address {ip}'
            Log.error(f'{reason}: {e}')
            raise CsmInternalError(reason) from e
        return [iface_data.to_native()]
