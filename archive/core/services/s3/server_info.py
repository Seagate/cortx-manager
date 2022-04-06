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

from csm.common.services import ApplicationService
from csm.common.service_urls import ServiceUrls
from csm.common.errors import InvalidRequest


class S3ServerInfoService(ApplicationService):
    """
    Service for acessing S3 server information
    """

    def get_s3_server_info(self, schemas):
        """
        Obtain information about S3 server in json format
        :param schemas: List of supported schemas for s3_server_info eg. http,https,s3
        :returns: s3_urls in json format based on the provided schemas
        """
        supported_schemas = ServiceUrls.get_s3_supported_schemas()
        if schemas is not None:
            if not all(s in supported_schemas for s in schemas):
                raise InvalidRequest(f'Unsupported schema in list of schemas {schemas}. '
                    f'Supported schemas are {supported_schemas}')
            s3_urls = [ServiceUrls.get_s3_uri(s) for s in schemas]
        else:
            s3_urls = [ServiceUrls.get_s3_uri(s) for s in supported_schemas]
        return {
            "s3_urls": s3_urls
        }
