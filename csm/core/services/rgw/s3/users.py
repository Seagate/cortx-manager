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

from cortx.utils.log import Log
from csm.core.blogic import const
from csm.core.data.models.rgw import RgwError
from csm.core.services.rgw.s3.utils import S3BaseService

class S3IAMUserService(S3BaseService):
    """S3 IAM user management service class."""

    def __init__(self, plugin):
        """
        Initializes s3_iam_plugin.

        :param plugin: s3_iam_plugin object
        :returns: None
        """
        self._s3_iam_plugin = plugin

    @Log.trace_method(Log.INFO)
    async def create_user(self, **user_body):
        """
        This method will create a new S3 IAM user.

        :param **user_body: User body kwargs
        """
        uid = user_body.get('uid')
        Log.debug(f"Creating S3 IAM user by uid = {uid}")
        plugin_response = self._s3_iam_plugin.execute(const.CREATE_USER_OPERATION, **user_body)
        if isinstance(plugin_response, RgwError):
            self._handle_error(plugin_response, args={'uid': uid})
        return plugin_response
