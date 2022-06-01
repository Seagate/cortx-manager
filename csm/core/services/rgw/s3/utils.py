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

from csm.core.data.models.rgw import RgwConnectionConfig
from csm.core.blogic import const
from csm.common.service_urls import ServiceUrls
from csm.common.conf import Security
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.security.cipher import CipherInvalidToken
from cortx.utils.log import Log


class CsmRgwConfigurationFactory:
    """Factory for the most common CSM RGW connections configurations."""

    @staticmethod
    def get_rgw_connection_config():
        """Creates a configuration for RGW connection."""
        rgw_connection_config = RgwConnectionConfig()
        rgw_endpoint = Conf.get(
            const.CSM_GLOBAL_INDEX, f'{const.RGW_S3_DATA_ENDPOINTS_KEY}[0]')
        _, host, port = ServiceUrls.parse_url(rgw_endpoint)
        rgw_connection_config.host = host
        rgw_connection_config.port = port
        rgw_connection_config.auth_user = Conf.get(
            const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ADMIN_USER)
        rgw_connection_config.auth_user_access_key = Conf.get(
            const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ACCESS_KEY)
        rgw_connection_config.auth_user_secret_key = \
            CsmRgwConfigurationFactory._get_decrypted_secret_key()
        return rgw_connection_config

    @staticmethod
    def _get_decrypted_secret_key():
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY)
        auth_user_secret_key = Conf.get(
            const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_SECRET_KEY)
        decreption_key = Conf.get(const.CSM_GLOBAL_INDEX,const.KEY_DECRYPTION)
        try:
            return Security.decrypt(auth_user_secret_key, cluster_id, decreption_key)
        except CipherInvalidToken as e:
            Log.error(f"Decryption failed: {e}")
