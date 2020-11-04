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

from typing import Any, Optional

from botocore.exceptions import ClientError
from cortx.utils.log import Log

from csm.common.conf import Conf
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.data.models.s3 import IamError, S3ConnectionConfig
from csm.plugins.cortx.s3 import IamClient


class CsmS3ConfigurationFactory:
    """Factory for the most common CSM S3 connections configurations"""
    @staticmethod
    def get_iam_connection_config():
        """Creates a configuration for S3 IAM connection"""
        iam_connection_config = S3ConnectionConfig()
        iam_connection_config.host = Conf.get(
            const.CSM_GLOBAL_INDEX, const.S3_HOST)
        iam_connection_config.port = Conf.get(
            const.CSM_GLOBAL_INDEX, const.S3_IAM_PORT)
        iam_connection_config.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX,
                                                         const.S3_MAX_RETRIES_NUM)
        return iam_connection_config

    @staticmethod
    def get_s3_connection_config():
        """Creates a configuration for S3 connection"""
        Log.debug("Get s3 connection config")
        s3_connection_config = S3ConnectionConfig()
        s3_connection_config.host = Conf.get(const.CSM_GLOBAL_INDEX, const.S3_HOST)
        s3_connection_config.port = Conf.get(
            const.CSM_GLOBAL_INDEX, const.S3_PORT)
        s3_connection_config.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.S3_MAX_RETRIES_NUM)
        return s3_connection_config


class IamRootClient(IamClient):
    """IAM client with the root privileges"""
    def __init__(self):
        ldap_login = Conf.get(const.CSM_GLOBAL_INDEX, const.S3_LDAP_LOGIN)
        # TODO: Password should be taken as input and not read from conf file directly.
        ldap_password = Conf.get(const.CSM_GLOBAL_INDEX, const.S3_LDAP_PASSWORD)
        iam_conf = CsmS3ConfigurationFactory.get_iam_connection_config()
        super().__init__(ldap_login, ldap_password, iam_conf)

    async def get_user(self, user_name):
        # TODO: Currently is not supported by IamRootClient.
        raise NotImplementedError()


class S3ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str, args: Optional[Any] = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.message_args = args


class S3BaseService(ApplicationService):
    @staticmethod
    def _handle_error(error, args: Optional[Any] = None):
        """A helper method for raising exceptions on S3-related errors"""
        # TODO: Change this method after unified error handling implementation in the S3 plugin.
        if isinstance(error, IamError):
            raise S3ServiceError(
                error.http_status, error.error_code.value, error.error_message, args)

        if isinstance(error, ClientError):
            error_code = error.response['Error']['Code']
            error_message = error.response["Error"]["Message"]
            http_status_code = error.response['ResponseMetadata']['HTTPStatusCode']
            # Can be useful? request_id = error.response['ResponseMetadata']['RequestId']
            raise S3ServiceError(http_status_code, error_code, error_message, args)
