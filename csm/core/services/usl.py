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

from boto.s3.bucket import Bucket
from functools import lru_cache
from ipaddress import ip_address
from typing import Any, Dict
from uuid import UUID, uuid4, uuid5

from csm.common.conf import Conf
from csm.common.errors import CsmInternalError
from csm.common.periodic import Periodic
from cortx.utils.data.access import Query
from cortx.utils.log import Log
from csm.common.runtime import Options
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.services.storage_capacity import StorageCapacityService
from csm.core.data.models.system_config import ApplianceName
from csm.core.data.models.usl import ApiKey
from csm.core.services.s3.utils import CsmS3ConfigurationFactory
from csm.plugins.cortx.provisioner import NetworkConfigFetchError
from csm.usl.models import Volume
from csm.usl.usl import USLDriver
from cortx.utils.security.secure_storage import SecureStorage
from cortx.utils.security.cipher import Cipher


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


class UslService(ApplicationService, USLDriver):
    """
    Implements USL service operations.
    """
    # FIXME improve token management
    _s3plugin: Any
    _api_key_dispatch: UslApiKeyDispatcher
    _secure_storage: SecureStorage

    def __init__(self, s3_plugin, storage, provisioner) -> None:
        """
        Constructor.
        """
        self._s3plugin = s3_plugin
        self._provisioner = provisioner
        self._storage = storage
        key = Cipher.generate_key(str(self.get_device_uuid()), 'USL')
        self._secure_storage = SecureStorage(self._storage, key)
        self._api_key_dispatch = UslApiKeyDispatcher(self._storage)

    def get_secure_storage(self) -> SecureStorage:
        return self._secure_storage

    @lru_cache(maxsize=1)
    def get_device_uuid(self) -> UUID:
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

    async def get_friendly_name(self) -> str:
        entries = await self._storage(ApplianceName).get(Query())
        appliance_name = next(iter(entries), None)
        if appliance_name is None:
            reason = 'Could not retrieve friendly name from storage'
            Log.error(f'{reason}')
            raise CsmInternalError(desc=reason)
        return str(appliance_name)

    async def _is_bucket_supported(self, s3_cli, bucket):
        """
        Checks if bucket is enabled for Lyve Pilot

        Buckets enabled for Lyve Pilot contain tag {Key=udx,Value=enabled}
        """

        tags = await s3_cli.get_bucket_tagging(bucket.name)
        return tags.get('udx', 'disabled') == 'enabled'

    async def _get_volume_name(self, bucket_name: str) -> str:
        return await self.get_friendly_name() + ": " + bucket_name

    def _get_volume_uuid(self, bucket_name: str) -> UUID:
        """Generates the CORTX volume (bucket) UUID from CORTX device UUID and bucket name."""
        return uuid5(self.get_device_uuid(), bucket_name)

    async def _format_bucket_as_volume(self, bucket: Bucket) -> Volume:
        bucket_name = bucket.name
        volume_name = await self._get_volume_name(bucket_name)
        device_uuid = self.get_device_uuid()
        volume_uuid = self._get_volume_uuid(bucket_name)
        capacity_details = await StorageCapacityService(self._provisioner).get_capacity_details()
        capacity_size = capacity_details[const.SIZE]
        capacity_used = capacity_details[const.USED]
        return Volume.instantiate(
            volume_name, bucket_name, device_uuid, volume_uuid, capacity_size, capacity_used)

    async def get_volume_list(
        self, access_key_id: str, secret_access_key: str
    ) -> Dict[UUID, Volume]:
        s3_client = self._s3plugin.get_s3_client(
            access_key_id, secret_access_key, CsmS3ConfigurationFactory.get_s3_connection_config()
        )
        volumes = {}
        for bucket in await s3_client.get_all_buckets():
            if not await self._is_bucket_supported(s3_client, bucket):
                continue
            volume = await self._format_bucket_as_volume(bucket)
            volumes[volume.uuid] = volume
        return volumes

    async def get_mgmt_url(self) -> Dict[str, str]:
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

    async def get_public_ip(self) -> str:
        """
        Reads UDS public IP from global index in an attempt to override UDS default behavior.
        If it is not found, uses cluster IP as UDS public IP.

        :return: A string representing UDS public IP address.
        """
        try:
            ip = Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.public_ip')
            ip_address(ip)
            return ip
        except ValueError as e:
            reason = 'UDS public IP override failed---following usual code path'
            Log.debug(f'{reason}. Error: {e}')
        try:
            conf = await self._provisioner.get_network_configuration()
            ip = conf.cluster_ip
            ip_address(ip)
            return ip
        except (ValueError, NetworkConfigFetchError) as e:
            reason = 'Could not obtain network configuration from provisioner'
            Log.error(f'{reason}: {e}')
            raise CsmInternalError(reason) from e
