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

from csm.core.blogic import const
from csm.core.controllers.view import CsmView
from cortx.utils.log import Log


@CsmView._app_routes.view("/api/v1/s3")
@CsmView._app_routes.view("/api/v2/s3")
class S3ServerInfoView(CsmView):
    """
    S3 Server Info View for GET REST API implementation:
        - Get information about the S3 server
    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self._request.app[const.S3_SERVER_INFO_SERVICE]

    async def get(self):
        """
        GET REST implementation for S3 server information request

        :return: s3_urls in json format
        """
        Log.debug(f"Handling list s3 buckets fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        schemas = self.request.rel_url.query.get("schemas")
        if schemas is not None:
            schemas = schemas.split(',')
        return self._service.get_s3_server_info(schemas)
