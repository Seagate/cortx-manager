# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020, 2021 Seagate Technology LLC and/or its Affiliates
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

from cortx.utils.conf_store.conf_store import Conf
from ipaddress import ip_address
from socket import gethostbyname, gaierror

from csm.core.blogic import const


class NetworkAddresses:
    """Helper class that manages CORTX network addresses."""

    @staticmethod
    def get_virtual_host_ip_addr() -> str:
        """
        Get virtual host IP address.

        :return: String representation of virtual host IP address
        """
        try:
            ip = str(Conf.get(const.USL_GLOBAL_INDEX, 'PROVISIONER>virtual_host'))
            ip_address(ip)
            return ip
        except ValueError as e:
            desc = 'Could not obtain management IP address from CSM config'
            raise RuntimeError(f'{desc}: {e}') from e

    @staticmethod
    def get_node_public_data_ip_addr() -> str:
        """
        Get public data IP address of the active node.

        :return: String representation of public data IP address
        """
        try:
            domain_name = \
                str(Conf.get(const.USL_GLOBAL_INDEX, 'PROVISIONER>node_public_data_domain_name'))
            ip = gethostbyname(domain_name)
            ip_address(ip)
            return ip
        except (ValueError, gaierror) as e:
            desc = 'Could not obtain data IP address from CSM config'
            raise RuntimeError(f'{desc}: {e}') from e
