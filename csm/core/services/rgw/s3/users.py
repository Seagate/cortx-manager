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

    async def execute_request(self, operation, **kwargs):

        plugin_response =await self._s3_iam_plugin.execute(operation, **kwargs)
        if isinstance(plugin_response, RgwError):
            self._handle_error(plugin_response)
        return plugin_response

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key', 'secret_key'])
    async def create_user(self, **user_body):
        """
        This method will create a new S3 IAM user.

        :param **user_body: User body kwargs
        """
        uid = user_body.get(const.RGW_JSON_UID)
        Log.debug(f"Creating S3 IAM user by uid = {uid}")
        return await self.execute_request(const.CREATE_USER_OPERATION, **user_body)

    @Log.trace_method(Log.DEBUG)
    async def get_user(self, **request_body):
        """
        Method to get existing S3 IAM user.

        :param **request_body: Request body kwargs
        """
        uid = request_body.get(const.RGW_JSON_UID)
        Log.debug(f"Fetching S3 IAM user by uid = {uid}")
        return await self.execute_request(const.GET_USER_OPERATION, **request_body)

    @Log.trace_method(Log.DEBUG)
    async def delete_user(self, **request_body):
        """
        Method to delete existing S3 IAM user.

        :param **request_body: Request body kwargs
        """
        uid = request_body.get(const.RGW_JSON_UID)
        Log.debug(f"Deleting S3 IAM user by uid = {uid}")
        return await self.execute_request(const.DELETE_USER_OPERATION, **request_body)

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key', 'secret_key'])
    async def create_key(self, **create_key_body):
        """
        This method will add/create access key to S3 IAM user.

        :param **create_key_body: User body kwargs
        """
        uid = create_key_body.get(const.RGW_JSON_UID)
        Log.debug(f"Creating Key for S3 IAM user by uid = {uid}")
        return await self.execute_request(const.CREATE_KEY_OPERATION, **create_key_body)

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key', 'secret_key'])
    async def remove_key(self, **remove_key_body):
        """
        This method will remove access key to S3 IAM user.

        :param **remove_key_body: User body kwargs
        """
        uid = remove_key_body.get(const.RGW_JSON_UID)
        Log.debug(f"Removing key for S3 IAM user by uid = {uid}")
        return await self.execute_request(const.REMOVE_KEY_OPERATION, **remove_key_body)

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key', 'secret_key'])
    async def add_user_caps(self, **request_body):
        """
        This method will add user caps for a new S3 IAM user.

        :param **request_body: User body kwargs
        """
        uid = request_body.get(const.RGW_JSON_UID)
        Log.debug(f"Add User caps for S3 IAM user by uid = {uid}")
        return await self.execute_request(const.ADD_USER_CAPS_OPERATION, **request_body)
