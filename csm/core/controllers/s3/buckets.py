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

import json
from marshmallow import Schema, fields, validate
from marshmallow.exceptions import ValidationError
from csm.core.controllers.validators import BucketNameValidator
from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.s3.base import S3AuthenticatedView
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.core.providers.providers import Response


class S3BucketCreationSchema(Schema):
    """
    Scheme for verification of POST request body for S3 bucket creation API

    """
    bucket_name = fields.Str(required=True, validate=[BucketNameValidator()])


@CsmView._app_routes.view("/api/v1/s3/bucket")
@CsmView._app_routes.view("/api/v2/s3/bucket")
class S3BucketListView(S3AuthenticatedView):
    """
    S3 Bucket List View for GET and POST REST API implementation:
        1. Get list of all existing buckets
        2. Create new bucket by given name
    """

    def __init__(self, request):
        super().__init__(request, 's3_bucket_service')

    @CsmAuth.permissions({Resource.S3BUCKETS: {Action.LIST}})
    async def get(self):
        """
        GET REST implementation for S3 buckets fetch request

        :return:
        """
        Log.debug(f"Handling list s3 buckets fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        # TODO: in future we can add some parameters for pagination
        with self._guard_service():
            return await self._service.list_buckets(self._s3_session)

    @CsmAuth.permissions({Resource.S3BUCKETS: {Action.CREATE}})
    async def post(self):
        """
        POST REST implementation for S3 buckets post request

        :return:
        """
        Log.debug(f"Handling create s3 buckets post request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = S3BucketCreationSchema()
            bucket_creation_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        with self._guard_service():
            # NOTE: body is empty
            result = await self._service.create_bucket(self._s3_session, **bucket_creation_body)
            return result


@CsmView._app_routes.view("/api/v1/s3/bucket/{bucket_name}")
@CsmView._app_routes.view("/api/v2/s3/bucket/{bucket_name}")
class S3BucketView(S3AuthenticatedView):
    """
    S3 Bucket view for DELETE REST API implementation:
        1. Delete bucket by its given name

    """

    def __init__(self, request):
        super().__init__(request, 's3_bucket_service')

    @CsmAuth.permissions({Resource.S3BUCKETS: {Action.DELETE}})
    async def delete(self):
        """
        DELETE REST implementation for s3 bucket delete request
        :return:
        """
        Log.debug(f"Handling s3 bucket delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        with self._guard_service():
            return await self._service.delete_bucket(bucket_name, self._s3_session)


@CsmView._app_routes.view("/api/v1/s3/bucket_policy/{bucket_name}")
@CsmView._app_routes.view("/api/v2/s3/bucket_policy/{bucket_name}")
class S3BucketPolicyView(S3AuthenticatedView):
    """
    S3 Bucket Policy View for GET, PUT and DELETE REST API implementation:
        1. Get bucket policy of existing bucket
        2. Create or update bucket policy by given bucket name
        3. Delete bucket policy by given bucket name
    """

    def __init__(self, request):
        super().__init__(request, 's3_bucket_service')

    """
    GET REST implementation for S3 bucket policy fetch request
    """
    @CsmAuth.permissions({Resource.S3BUCKET_POLICY: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling s3 bucket policy fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        with self._guard_service():
            return await self._service.get_bucket_policy(self._s3_session,
                                                         bucket_name)

    """
    PUT REST implementation for S3 bucket policy put request
    """
    @CsmAuth.permissions({Resource.S3BUCKET_POLICY: {Action.CREATE}})
    async def put(self):
        Log.debug(f"Handling s3 bucket policy put request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        bucket_policy_body = await self.request.json()
        with self._guard_service():
            return await self._service.put_bucket_policy(self._s3_session,
                                                         bucket_name,
                                                         bucket_policy_body)

    """
    DELETE REST implementation for s3 bucket policy delete request
    """
    @CsmAuth.permissions({Resource.S3BUCKET_POLICY: {Action.DELETE}})
    async def delete(self):
        Log.debug(f"Handling s3 bucket policy delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        with self._guard_service():
            return await self._service.delete_bucket_policy(self._s3_session,
                                                            bucket_name)
