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

from typing import Union

from botocore.exceptions import ClientError
from boto.s3.bucket import Bucket

from cortx.utils.log import Log
from csm.common.services import ApplicationService

from csm.plugins.eos.s3 import S3Plugin, S3Client
from csm.core.providers.providers import Response
from csm.core.services.sessions import S3Credentials
from csm.core.services.s3.utils import S3BaseService, CsmS3ConfigurationFactory


# TODO: the access to this service must be restricted to CSM users only (?)
class S3BucketService(S3BaseService):
    """
    Service for S3 account management
    """

    def __init__(self, s3plugin: S3Plugin):
        self._s3plugin = s3plugin
        self._s3_connection_config = CsmS3ConfigurationFactory.get_s3_connection_config()

    async def get_s3_client(self, s3_session: S3Credentials) -> S3Client:
        """
        Create S3 Client object for S3 session user

        :param s3_session: S3 Account information
        :type s3_session: S3Credentials
        :return:
        """
        # TODO: it should be a common method for all services
        return self._s3plugin.get_s3_client(access_key=s3_session.access_key,
                                            secret_key=s3_session.secret_key,
                                            connection_config=self._s3_connection_config,
                                            session_token=s3_session.session_token)

    @Log.trace_method(Log.INFO)
    async def create_bucket(self, s3_session: S3Credentials,
                            bucket_name: str) -> Union[Response, Bucket]:
        """
        Create new bucket by given name

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :param bucket_name: name of bucket for creation
        :type bucket_name: str
        :return:
        """
        Log.debug(f"Requested to create bucket by name = {bucket_name}")
        try:
            s3_client = await self.get_s3_client(s3_session)  # type: S3Client
            bucket = await s3_client.create_bucket(bucket_name)
        except ClientError as e:
            # TODO: distinguish errors when user is not allowed to get/delete/create buckets
            self._handle_error(e)

        return {"bucket_name": bucket_name}  # bucket Can be None

    @Log.trace_method(Log.INFO)
    async def list_buckets(self, s3_session: S3Credentials) -> dict:
        """
        Retrieve the full list of existing buckets

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :return:
        """
        # TODO: pagination can be added later
        Log.debug(f"Retrieve the whole list of buckets for active user session")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            bucket_list = await s3_client.get_all_buckets()
        except ClientError as e:
            # TODO: distinguish errors when user is not allowed to get/delete/create buckets
            self._handle_error(e)

        # TODO: create model for response
        bucket_list = [{"name": bucket.name} for bucket in bucket_list]
        return {"buckets": bucket_list}

    @Log.trace_method(Log.INFO)
    async def delete_bucket(self, bucket_name: str, s3_session: S3Credentials):
        """
        Delete bucket by given name

        :param bucket_name: name of bucket for creation
        :type bucket_name: str
        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :return:
        """
        Log.debug(f"Requested to delete bucket by name = {bucket_name}")

        s3_client = await self.get_s3_client(s3_session)  # TODO: s3_client can't be returned
        try:
            # NOTE: returns None if deletion is successful
            await s3_client.delete_bucket(bucket_name)
        except ClientError as e:
            self._handle_error(e)
        return {"message": "Bucket Deleted Successfully."}
    @Log.trace_method(Log.INFO)
    async def get_bucket_policy(self, s3_session: S3Credentials,
                                bucket_name: str) -> dict:
        """
        Retrieve the policy of existing bucket

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :returns: A dict of bucket policy
        """
        Log.debug(f"Retrieve bucket bucket by name = {bucket_name}")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            bucket_policy = await s3_client.get_bucket_policy(bucket_name)
        except ClientError as e:
            self._handle_error(e)
        return bucket_policy

    @Log.trace_method(Log.INFO)
    async def put_bucket_policy(self, s3_session: S3Credentials, bucket_name: str,
                                policy: dict) -> dict:
        """
        Create or update the policy of existing bucket

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :returns: Success message
        """
        Log.debug(
            f"Requested to put bucket policy for bucket name = {bucket_name}")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            bucket_policy = await s3_client.put_bucket_policy(bucket_name, policy)
        except ClientError as e:
            self._handle_error(e)
        return {"message": "Bucket Policy Updated Successfully."}

    @Log.trace_method(Log.INFO)
    async def delete_bucket_policy(self, s3_session: S3Credentials,
                                bucket_name: str) -> dict:
        """
        Delete the policy of existing bucket

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :returns: Success message
        """
        Log.debug(
            f"Requested to delete bucket policy for bucket name = {bucket_name}")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            bucket_policy = await s3_client.delete_bucket_policy(bucket_name)
        except ClientError as e:
            self._handle_error(e)
        return {"message": "Bucket Policy Deleted Successfully."}

