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

from aiohttp import ClientError as HttpClientError
from aiohttp import ClientSession, TCPConnector
from cortx.utils.log import Log
from marshmallow import ValidationError
from marshmallow.validate import URL
from random import SystemRandom
from typing import Dict

from csm.common.conf import Conf
from csm.common.errors import (
    CsmGatewayTimeout, CsmInternalError, CsmNotFoundError, InvalidRequest)
from csm.core.blogic import const
from csm.core.services.lyve_pilot_s3 import LyvePilotS3BucketsManager


class LyvePilotExtensionsService:
    async def get_saas_url(self) -> Dict[str, str]:
        """
        Obtains Lyve Pilot SaaS URL from CSM global index and returns it to the user.
        If it is not found, raise status code 404.

        :return: Dictionary containing SaaS URL
        """
        saas_url = Conf.get(const.CSM_GLOBAL_INDEX, 'UDS.saas_url')
        if saas_url is None:
            reason = 'Lyve Pilot SaaS URL is not configured'
            Log.debug(reason)
            raise CsmNotFoundError(desc=reason)
        try:
            validate_url = URL(schemes=('https'))
            validate_url(saas_url)
        except ValidationError:
            reason = f'Invalid Lyve Pilot SaaS URL: {saas_url}'
            Log.error(reason)
            raise CsmInternalError(desc=reason)
        return {'saas_url': saas_url}

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
        # XXX Registration body is currently validated by view and by UDS
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
        buckets_controller = LyvePilotS3BucketsManager(
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
