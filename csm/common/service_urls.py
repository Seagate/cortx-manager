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


from typing import List

from cortx.utils.conf_store.conf_store import Conf
from csm.common.network_addresses import NetworkAddresses
from csm.core.blogic import const


class ServiceUrls:
    """
    Helper class that manages CORTX URLS.

    Provides various CORTX URLs retrieved from the provisioner in a clean and user-friendly format.
    """

    @staticmethod
    def get_mgmt_url() -> str:
        """
        Return the management URL for the appliance.

        :returns: management URL as a string.
        """
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE>CSM_WEB>ssl_check')
        scheme = 'https' if ssl_check else 'http'
        host = NetworkAddresses.get_virtual_host_ip_addr()
        port = \
            Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE>CSM_WEB>port') or const.WEB_DEFAULT_PORT
        url = f'{scheme}://{host}:{port}'
        return url

    @staticmethod
    def get_s3_uri(scheme: str = 's3') -> str:
        """
        Obtain the S3 server URI.

        :param scheme: URI scheme
        :returns: S3 server URI based on the provided scheme
        """
        ip = NetworkAddresses.get_node_public_data_ip_addr()
        if scheme == 's3':
            port = Conf.get(const.CSM_GLOBAL_INDEX, 'S3>s3_port')
            uri = f'{scheme}://{ip}:{port}'
        else:
            uri = f'{scheme}://{ip}'
        return uri

    @staticmethod
    def get_s3_supported_schemas() -> List[str]:
        """
        Obtain a list of S3 supported schemas.

        :returns: List of S3 supported schemas.
        """
        return ['http', 'https', 's3']

    @staticmethod
    def get_bucket_url(bucket_name: str, scheme: str) -> str:
        """
        Obtain a bucket URL.

        :param scheme: URL scheme
        :param bucket_name: Bucket name to be appended to the URL as its path
        :returns: Bucket URL
        """
        return '{}/{}'.format(ServiceUrls.get_s3_uri(scheme), bucket_name)
