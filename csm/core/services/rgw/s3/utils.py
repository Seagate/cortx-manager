# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
from csm.core.data.models.rgw import RgwConnectionConfig
from csm.common.services import ApplicationService
from csm.core.data.models.rgw import RgwError
from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf

class CsmRgwConfigurationFactory:
    """Factory for the most common CSM RGW connections configurations."""

    @staticmethod
    def get_rgw_connection_config():
        """Creates a configuration for RGW connection."""
        rgw_connection_config = RgwConnectionConfig()
        # ToDo: Read host port values from csm configuration
        rgw_endpoint = Conf.get(
            const.CSM_GLOBAL_INDEX, 'RGW>s3>iam>endpoints[0]')
        protocol, host, port = CsmRgwConfigurationFactory._parse_endpoints(rgw_endpoint)
        rgw_connection_config.host = host
        rgw_connection_config.port = int(port)
        # ToDo: Replace the keys with consts
        # ToDo: Remove default values once keys are available in conf store
        rgw_connection_config.auth_user = Conf.get(
            const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ADMIN_USER, 'admin')
        rgw_connection_config.auth_user_access_key = Conf.get(
            const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ACCESS_KEY)
        rgw_connection_config.auth_user_secret_key = Conf.get(
            const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_SECRET_KEY)
        return rgw_connection_config

    @staticmethod
    def _parse_endpoints(url):
        """
        Parse RGW endpoint.

        :returns protocol: RGW connection protocol
        :returns host: RGW connection host
        :returns port: RGW connection port

        """
        if "://"in url:
            protocol, endpoint = url.split("://")
        else:
            protocol = ''
            endpoint = url
        host, port = endpoint.split(":")
        return protocol, host, port

class S3ServiceError(Exception):
    """S3 service error class."""

    def __init__(self, status: int, code: str, message: str, args: Optional[Any] = None) -> None:
        """S3 Service Error init."""
        self.status = status
        self.code = code
        self.message = message
        self.message_args = args

class S3BaseService(ApplicationService):
    def _handle_error(self, error, args: Optional[Any] = None):
        """A helper method for raising exceptions on S3 related errors."""

        if isinstance(error, RgwError):
            raise S3ServiceError(error.http_status,
                                 error.error_code.name,
                                 error.error_message,
                                 args)
