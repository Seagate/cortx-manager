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

from typing import Dict
from cortx.utils.log import Log
from csm.core.services.s3.buckets import S3BucketService
from csm.core.services.sessions import S3Credentials


class UslS3BucketsManager:
    def __init__(
        self,
        s3_bucket_service: S3BucketService,
        account_name: str,
        access_key: str,
        secret_access_key: str,
    ) -> None:
        self._s3_credentials =  S3Credentials(account_name, access_key, secret_access_key, '')
        self._s3_bucket_service = s3_bucket_service

    async def _get_bucket_tagging(self, bucket_name: str) -> Dict:
        return await self._s3_bucket_service.get_bucket_tagging(self._s3_credentials, bucket_name)

    async def _put_bucket_tagging(self, bucket_name, tagging) -> None:
        await self._s3_bucket_service.put_bucket_tagging(
            self._s3_credentials, bucket_name, tagging['tagset'])

    async def enable_lyve_pilot(self, bucket_name: str) -> None:
        tagging = await self._get_bucket_tagging(bucket_name)
        tagging['tagset']['udx'] = 'enabled'
        await self._put_bucket_tagging(bucket_name, tagging)
        Log.debug(f'Lyve Pilot support enabled on bucket {bucket_name}')

    async def disable_lyve_pilot(self, bucket_name: str) -> None:
        tagging = await self._get_bucket_tagging(bucket_name)
        tagging['tagset']['udx'] = 'disabled'
        await self._put_bucket_tagging(bucket_name, tagging)
        Log.debug(f'Lyve Pilot support disabled on bucket {bucket_name}')
