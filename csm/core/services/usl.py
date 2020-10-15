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
from datetime import date
from random import SystemRandom
from marshmallow import ValidationError
from marshmallow.validate import URL
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4, uuid5

from csm.common.conf import Conf
from csm.common.errors import (
    CsmGatewayTimeout, CsmInternalError, CsmNotFoundError, CsmPermissionDenied)
from csm.common.periodic import Periodic
from cortx.utils.data.access import Query
from cortx.utils.log import Log
from csm.common.runtime import Options
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.services.storage_capacity import StorageCapacityService
from csm.core.services.sessions import S3Credentials
from csm.core.services.s3.accounts import S3AccountService
from csm.core.services.s3.iam_users import IamUsersService
from csm.core.services.s3.buckets import S3BucketService
from csm.core.data.models.system_config import ApplianceName
from csm.core.data.models.usl import Device, Volume, ApiKey
from csm.core.services.s3.utils import CsmS3ConfigurationFactory
from csm.core.services.usl_net_ifaces import get_interface_details
from csm.core.services.usl_certificate_manager import (
    USLDomainCertificateManager, USLNativeCertificateManager, CertificateError
)
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
    _token: str
    _s3plugin: Any
    _domain_certificate_manager: USLDomainCertificateManager
    _native_certificate_manager: USLNativeCertificateManager
    _api_key_dispatch: UslApiKeyDispatcher

    def __init__(self, s3_plugin, storage, provisioner) -> None:
        """
        Constructor.
        """
        self._token = ''
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

    def _format_lyve_pilot_register_device_params(
        self, url: str, pin: str, token: str
    ) -> Dict[str, str]:
        register_device_params = {
            'url': url,
            'regPin': pin,
            'regToken': token,
        }
        return register_device_params

    async def _format_lyve_pilot_access_params(self, s3_account: Dict,
                                               iam_user: Dict) -> Dict[str, Any]:
        network = await self._provisioner.get_network_configuration()
        access_params = {
            'accountName': s3_account.get('account_name'),
            # TODO find a better way to obtain S3 server host and port
            'uri': 's3://{}:{}'.format(
                network.cluster_ip,
                Conf.get(const.CSM_GLOBAL_INDEX, 'S3.s3_port'),
            ),
            'credentials': {
                'accessKey': iam_user.get('access_key_id'),
                'secretKey': iam_user.get('secret_key'),
            },
        }
        return access_params

    async def _cleanup(self,
                       s3_account_service: S3AccountService,
                       s3_iam_users_service: IamUsersService,
                       s3_bucket_service: S3BucketService,
                       s3_credentials: Optional[S3Credentials],
                       s3_account_name: Optional[str],
                       iam_user_name: Optional[str],
                       bucket_name: Optional[str]) -> None:
        if s3_credentials is None:
            Log.debug('No cleaning to be done')
            return
        try:
            if bucket_name is not None:
                Log.debug(f'Deleting bucket {bucket_name}')
                await s3_bucket_service.delete_bucket(bucket_name, s3_credentials)
            if iam_user_name is not None:
                Log.debug(f'Deleting IAM user {iam_user_name}')
                await s3_iam_users_service.delete_user(s3_credentials, iam_user_name)
            if s3_account_name is not None:
                Log.debug(f'Deleting S3 account {s3_account_name}')
                await s3_account_service.delete_account(s3_credentials, s3_account_name)
        except Exception as e:
            # Supress any errors from the cleanup, don't bother the user
            Log.error(f'Cleanup failed --- {str(e)}')

    async def _initialize_lyve_pilot_s3_resources(
        self,
        s3_account_service: S3AccountService,
        s3_iam_users_service: IamUsersService,
        s3_bucket_service: S3BucketService,
        s3_account_name: str,
        s3_account_email: str,
        s3_account_password: str,
        iam_user_name: str,
        iam_user_password: str,
        bucket_name: str,
    ) -> Tuple[S3Credentials, Dict, Dict, Dict]:
        s3_credentials: Optional[S3Credentials] = None
        lyve_pilot_acc_name: Optional[str] = None
        lyve_pilot_user_name: Optional[str] = None
        lyve_pilot_bucket_name: Optional[str] = None

        try:
            Log.debug('Create S3 account')
            s3_account = await s3_account_service.create_account(
                s3_account_name, s3_account_email, s3_account_password)
            lyve_pilot_acc_name = s3_account.get('account_name')
            s3_credentials = S3Credentials(
                lyve_pilot_acc_name,
                str(s3_account.get('access_key')),
                str(s3_account.get('secret_key')),
                '')
            Log.debug('Create IAM user')
            iam_user = await s3_iam_users_service.create_user(
                s3_credentials, iam_user_name, iam_user_password)
            lyve_pilot_user_name = str(iam_user.get('user_name'))
            Log.debug('Create bucket')
            bucket = await s3_bucket_service.create_bucket(s3_credentials, bucket_name)
            lyve_pilot_bucket_name = str(bucket.get('bucket_name'))
            Log.debug('Tag bucket')
            await self._tag_lyve_pilot_bucket(s3_credentials, s3_bucket_service, bucket_name)
            Log.debug('Put bucket policy')
            iam_user_arn = str(iam_user.get('arn'))
            await self._set_lyve_pilot_policy(s3_credentials, s3_bucket_service, iam_user_arn,
                                              bucket_name)
        except Exception as e:
            await self._cleanup(s3_account_service,
                                s3_iam_users_service,
                                s3_bucket_service,
                                s3_credentials,
                                lyve_pilot_acc_name,
                                lyve_pilot_user_name,
                                lyve_pilot_bucket_name)
            reason = 'S3 resources preparation failed'
            Log.error(f'{reason}---{str(e)}')
            raise e
        return (s3_credentials, s3_account, iam_user, bucket)

    async def _is_bucket_lyve_pilot_enabled(self, s3_cli, bucket):
        """
        Checks if bucket is enabled for Lyve Pilot

        Buckets enabled for Lyve Pilot contain tag {Key=udx,Value=enabled}
        """

        tags = await s3_cli.get_bucket_tagging(bucket)
        return tags.get('udx', 'disabled') == 'enabled'

    async def _tag_lyve_pilot_bucket(self, s3_credentials: S3Credentials,
                                     s3_bucket_service: S3BucketService, bucket_name: str) -> None:
        """
        Puts the Lyve Pilot tag on a specified bucket
        """
        bucket_tags = {"udx": "enabled"}
        await s3_bucket_service.put_bucket_tagging(s3_credentials, bucket_name, bucket_tags)
        Log.info(f'Lyve Pilot bucket {bucket_name} is taggged with {bucket_tags}')

    async def _set_lyve_pilot_policy(self, s3_credentials: S3Credentials,
                                     s3_bucket_service: S3BucketService, iam_user_arn: str,
                                     bucket_name: str) -> None:
        """
        Grants the specified IAM user full access to the specified bucket
        """
        policy = {
            'Version': str(date.today()),
            'Statement': [{
                'Sid': 'UdxIamAccountPerm',
                'Effect': 'Allow',
                'Principal': {"AWS": iam_user_arn},
                'Action': ['s3:GetObject', 's3:PutObject',
                           's3:ListMultipartUploadParts', 's3:AbortMultipartUpload',
                           's3:GetObjectAcl', 's3:PutObjectAcl',
                           's3:PutObjectTagging',
                           # TODO: now S3 server rejects the following policies
                           # 's3:DeleteObject', 's3:RestoreObject', 's3:DeleteObjectTagging',
                           ],
                'Resource': f'arn:aws:s3:::{bucket_name}/*',
            }]
        }
        await s3_bucket_service.put_bucket_policy(s3_credentials, bucket_name, policy)
        Log.info(
            f'Lyve Pilot policy is set for bucket {bucket_name} and IAM user (arn) {iam_user_arn}')

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
        return [v.to_primitive(role='public') for _,v in volumes.items()]

    async def _handle_lyve_pilot_volume_mount_umount(
        self, device_id: UUID, volume_id: UUID, uri: str,
        access_key_id: str, secret_access_key: str, mount=True,
    ) -> Dict[str, str]:
        """
        Handles Lyve Pilot volume mount/umount

        Checks the device and the volume with the specified IDs exist and return
        the required mount/umount information
        """
        if device_id != self._device_uuid:
            raise CsmNotFoundError(desc=f'Device with ID {device_id} is not found')
        volumes = await self._get_lyve_pilot_volume_list(access_key_id, secret_access_key)
        if volume_id not in volumes:
            raise CsmNotFoundError(desc=f'Volume with ID {volume_id} is not found '
                                        f'on the device with ID {device_id}')
        if mount:
            return {
                'mountPath': volumes[volume_id].bucketName,
                'handle': volumes[volume_id].bucketName
            }
        else:
            return volumes[volume_id].bucketName

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
        return await self._handle_lyve_pilot_volume_mount_umount(
            device_id, volume_id, uri, access_key_id, secret_access_key, mount=True)

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
        return await self._handle_lyve_pilot_volume_mount_umount(
            device_id, volume_id, uri, access_key_id, secret_access_key, mount=False)

    async def get_events(self) -> None:
        """
        Returns USL events one-by-one
        """
        # TODO implement
        pass

    async def post_register_device(
        self,
        s3_account_service: S3AccountService,
        s3_iam_users_service: IamUsersService,
        s3_bucket_service: S3BucketService,
        url: str,
        pin: str,
        s3_account_name: str,
        s3_account_email: str,
        s3_account_password: str,
        iam_user_name: str,
        iam_user_password: str,
        bucket_name: str,
    ) -> Dict:
        """
        Executes device registration sequence. Communicates with the UDS server in order to start
        registration and verify its status.

        :param url: Registration URL as provided by the Lyve Pilot portal
        :param pin: Registration PIN as provided by the Lyve Pilot portal
        """
        uds_url = Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.url') or const.UDS_SERVER_DEFAULT_BASE_URL
        try:
            validate_url = URL(schemes=('http', 'https'))
            validate_url(uds_url)
        except ValidationError:
            reason = 'UDS base URL is not valid'
            Log.error(reason)
            raise CsmInternalError(desc=reason)
        # Let ``_initialize_lyve_pilot_s3_resources()`` propagate its exceptions
        (lyve_pilot_s3_credentials, lyve_pilot_s3_account, lyve_pilot_iam_user,
         lyve_pilot_bucket) = await self._initialize_lyve_pilot_s3_resources(
            s3_account_service,
            s3_iam_users_service,
            s3_bucket_service,
            s3_account_name,
            s3_account_email,
            s3_account_password,
            iam_user_name,
            iam_user_password,
            bucket_name,
        )
        try:
            register_device_params = self._format_lyve_pilot_register_device_params(
                url, pin, self._token)
            access_params = await self._format_lyve_pilot_access_params(
                lyve_pilot_s3_account,
                lyve_pilot_iam_user,
            )
            registration_body = {
                'registerDeviceParams': register_device_params,
                'accessParams': access_params,
            }
        except Exception as e:
            await self._cleanup(
                s3_account_service,
                s3_iam_users_service,
                s3_bucket_service,
                lyve_pilot_s3_credentials,
                lyve_pilot_s3_account.get('account_name'),
                lyve_pilot_iam_user.get('user_name'),
                lyve_pilot_bucket.get('bucket_name'),
            )
            reason = 'Error on registration body assembly'
            Log.error(f'{reason}---{str(e)}')
            raise CsmInternalError(desc=reason)
        try:
            endpoint_url = str(uds_url) + '/uds/v1/registration/RegisterDevice'
            # FIXME add relevant certificates to SSL context instead of disabling validation
            async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
                Log.info(f'Start device registration at {uds_url}')
                async with session.put(endpoint_url, json=registration_body) as response:
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
                return {
                    's3_account': {
                        'access_key': lyve_pilot_s3_account['access_key'],
                        'secret_key': lyve_pilot_s3_account['secret_key'],
                    },
                    'iam_user': {
                        'access_key': access_params['credentials']['accessKey'],
                        'secret_key': access_params['credentials']['secretKey'],
                    },
                }
        except Exception as e:
            await self._cleanup(
                s3_account_service,
                s3_iam_users_service,
                s3_bucket_service,
                lyve_pilot_s3_credentials,
                lyve_pilot_s3_account.get('account_name'),
                lyve_pilot_iam_user.get('user_name'),
                lyve_pilot_bucket.get('bucket_name'),
            )
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
        self._token = ''.join(SystemRandom().sample('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 12))
        return {'registrationToken': self._token}

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
    async def get_system(self) -> Dict[str, str]:
        """
        Provides information about the system.

        :return: A dictionary containing system information.
        """
        friendly_name = await self._get_system_friendly_name()
        service_urls = await self._get_service_urls()
        return {
            'model': 'CORTX',
            'type': 'ees',
            'serialNumber': self._device_uuid,
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
            ip = conf.mgmt_vip
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
