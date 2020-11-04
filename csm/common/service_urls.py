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


from typing import Union, List

from csm.common.conf import Conf
from csm.core.blogic import const


class ServiceUrls:
    """
    Helper class that manages CORTX URLS.

    Provides various CORTX URLs retrieved from the provisioner in a clean and user-friendly format.
    """

    def __init__(self, provisioner):
        """
        Initialize ServiceUrls.

        :param provisioner: provisioner object.
        """
        self._provisioner = provisioner

    async def get_mgmt_url(self) -> str:
        """
        Return the management URL for the appliance.

        :returns: management URL as a string.
        """
        network_configuration = await self._provisioner.get_network_configuration()
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE.CSM_WEB.ssl_check')
        port = \
            Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE.CSM_WEB.port') or const.WEB_DEFAULT_PORT
        scheme = 'https' if ssl_check else 'http'
        url = f'{scheme}://{network_configuration.mgmt_vip}:{port}'
        return url

    async def get_s3_url(self, scheme: str = None,
                         bucket_name: str = None) -> Union[List[str], str]:
        """
        Return an S3 server's URL.

        :param scheme: (optional) scheme of the required URL, if not set (default) - the list of
                        all possible URLs will be returned
        :param bucket_name: (optional) bucket's name to be included into the URL.
        :returns: S3 server's URL as a string.
        """
        network_configuration = await self._provisioner.get_network_configuration()
        url = f'{network_configuration.cluster_ip}'
        if bucket_name is not None:
            url += f'/{bucket_name}'
        if scheme is not None:
            return f'{scheme}://{url}'
        schemes = ['http', 'https']
        return [f'{sch}://{url}' for sch in schemes]
