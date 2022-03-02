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

class BucketService(S3BaseService):
    """
    S3 Bucket Operation service class.
    service method of all bucket operations
    entry point: execute()
    exit point: execute_request()
    """

    def __init__(self, plugin):
        """
        Initializes s3_bucket_plugin.
        :param plugin: s3_bucket_plugin object
        :returns: None
        """
        self._s3_bucket_plugin = plugin

    async def execute_request(self, operation, **kwargs):
        plugin_response =await self._s3_bucket_plugin.execute(operation, **kwargs)
        if isinstance(plugin_response, RgwError):
            self._handle_error(plugin_response)
        return plugin_response

    @Log.trace_method(Log.DEBUG)
    async def link_bucket(self, **request_body):
        """
        This method will Link bucket to user.

        :param **request_body: bucket body kwargs
        """
        uid = request_body.get(const.RGW_JSON_UID)
        Log.debug(f"Link bucket for S3 bucket to uid = {uid}")
        return await self.execute_request(const.BUCKET_LINK_OPERATION, **request_body)

    @Log.trace_method(Log.DEBUG)
    async def unlink_bucket(self, **request_body):
        """
        This method will unlink bucket from User.

        :param **request_body: bucket body kwargs
        """
        uid = request_body.get(const.RGW_JSON_UID)
        Log.debug(f"Unlink bucket from  uid = {uid}")
        return await self.execute_request(const.BUCKET_UNLINK_OPERATION, **request_body)

    operation_service_map = {
        const.LINK_BUCKET_OPERATION : link_bucket,
        const.UNLINK_BUCKET_OPERATION : unlink_bucket
    }

    @Log.trace_method(Log.DEBUG)
    async def execute(self, operation, **request_body):
        """
        execute will be called from controller
        operation(string) : bucket operation
        """
        Log.debug(f"Bucket Operation:- {operation} for S3 user")

        return await self.operation_service_map[operation](**request_body)
