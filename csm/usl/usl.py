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

from abc import ABC 
from typing import Any, Dict, List
from uuid import UUID

from cortx.utils.log import Log
from cortx.utils.security.secure_storage import SecureStorage
from csm.common.errors import (CsmInternalError, CsmNotFoundError, CsmPermissionDenied)
from csm.usl.models import Device, Volume
from csm.usl.net_ifaces import get_interface_details
from csm.usl.certificate_manager import (
    USLDomainCertificateManager, USLNativeCertificateManager, CertificateError
)


class USLDriver(ABC):
    def get_secure_storage(self) -> SecureStorage: ...

    async def get_friendly_name(self) -> str: ...

    def get_device_uuid(self) -> UUID: ...

    async def get_volume_list(self, _2: str, _3: str) -> Dict[UUID, Volume]: ...

    async def get_mgmt_url(self) -> Dict[str, str]: ...

    async def get_public_ip(self) -> str: ...


class USL:
    _driver: USLDriver
    _domain_certificate_manager: USLDomainCertificateManager
    _native_certificate_manager: USLNativeCertificateManager

    def __init__(self, driver: USLDriver) -> None:
        self._driver = driver
        self._domain_certificate_manager = USLDomainCertificateManager(
            self._driver.get_secure_storage())
        self._native_certificate_manager = USLNativeCertificateManager()

    # TODO replace stub
    async def _format_device_info(self) -> Device:
        device_uuid = self._driver.get_device_uuid()
        return Device.instantiate(
            await self._driver.get_friendly_name(),
            '0000',
            str(device_uuid),
            'S3',
            device_uuid,
            'Seagate',
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
        if device_id != self._driver.get_device_uuid():
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')
        volumes = await self._driver.get_volume_list(access_key_id, secret_access_key)
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
        if device_id != self._driver.get_device_uuid():
            raise CsmNotFoundError(desc=f'Device {device_id} not found')
        volumes = await self._driver.get_volume_list(access_key_id, secret_access_key)
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

    async def _get_service_urls(self) -> List[Dict[str, str]]:
        """
        Gathers all service URLs to be provided to the UDS.

        :return: a list of service URLs.
        """

        service_urls = []
        mgmt_url = await self._driver.get_mgmt_url()
        service_urls.append(mgmt_url)
        return service_urls

    # TODO replace stub
    async def get_system(self) -> Dict[str, Any]:
        """
        Provides information about the system.

        :return: A dictionary containing system information.
        """
        friendly_name = await self._driver.get_friendly_name()
        service_urls = await self._get_service_urls()
        return {
            'model': 'CORTX',
            'type': 'ees',
            'serialNumber': str(self._driver.get_device_uuid()),
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
        Provides a list of network interfaces to be advertised by UDS.

        :return: A list containing dictionaries, each containing information about a specific
            network interface.
        """
        try:
            ip = await self._driver.get_public_ip()
            iface_data = get_interface_details(ip)
        except (ValueError, RuntimeError) as e:
            reason = f'Could not obtain interface details from address {ip}'
            Log.error(f'{reason}: {e}')
            raise CsmInternalError(reason) from e
        return [iface_data.to_native()]
