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

from typing import Dict

from botocore.exceptions import ClientError

from cortx.utils.log import Log

from csm.plugins.cortx.s3 import S3Plugin, S3Client
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
        return self._s3plugin.get_s3_client(access_key_id=s3_session.access_key,
                                            secret_access_key=s3_session.secret_key,
                                            connection_config=self._s3_connection_config,
                                            session_token=s3_session.session_token)

    @Log.trace_method(Log.INFO)
    async def create_bucket(self, s3_session: S3Credentials,
                            bucket_name: str) -> Dict:
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
        return {
            "bucket_name": bucket_name,
        }  # bucket Can be None

    @Log.trace_method(Log.INFO)
    async def list_buckets(self, s3_session: S3Credentials) -> Dict:
        """
        Retrieve the full list of existing buckets

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :return:
        """
        # TODO: pagination can be added later
        Log.debug("Retrieve the whole list of buckets for active user session")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            bucket_list = await s3_client.get_all_buckets()
        except ClientError as e:
            # TODO: distinguish errors when user is not allowed to get/delete/create buckets
            self._handle_error(e)

        # TODO: create model for response
        bucket_list = [
            {
                "name": bucket.name,
            }
            for bucket in bucket_list]
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
        return {"message": f"Bucket {bucket_name} Deleted Successfully."}
    @Log.trace_method(Log.INFO)
    async def get_bucket_policy(self, s3_session: S3Credentials,
                                bucket_name: str) -> Dict:
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
                                policy: Dict) -> Dict:
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
                                bucket_name: str) -> Dict:
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

    @Log.trace_method(Log.INFO)
    async def get_bucket_tagging(self, s3_session: S3Credentials, bucket_name: str) -> Dict:
        """
        Get tags of the provided bucket

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :returns: tagset of the provided bucket
        """
        Log.debug(f"Put tags to the bucket {bucket_name}")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            tags = await s3_client.get_bucket_tagging(bucket_name)
        except ClientError as e:
            self._handle_error(e)
        return {"tagset": tags}

    @Log.trace_method(Log.INFO)
    async def put_bucket_tagging(self, s3_session: S3Credentials,
                                 bucket_name: str, bucket_tags: Dict) -> Dict:
        """
        Put provided tags onto the bucket

        :param s3_session: s3 user session
        :type s3_session: S3Credentials
        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :param bucket_tags: tags to be put onto the bucket
        :type bucket_tags: dict
        :returns: Success message
        """
        Log.debug(f"Put tags to the bucket {bucket_name}")
        s3_client = await self.get_s3_client(s3_session)  # type: S3Client
        try:
            await s3_client.put_bucket_tagging(bucket_name, bucket_tags)
        except ClientError as e:
            self._handle_error(e)
        return {"message": "Tagged the bucket successfully"}
