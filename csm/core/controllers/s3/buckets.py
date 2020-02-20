#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          buckets.py
 Description:       Implementation of buckets view

 Creation Date:     11/19/2019
 Author:            Dmitry Didenko

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json
from marshmallow import Schema, fields, validate
from marshmallow.exceptions import ValidationError
from csm.core.controllers.view import CsmView
from csm.common.log import Log
from csm.common.errors import InvalidRequest
from csm.core.providers.providers import Response


class S3BucketCreationSchema(Schema):
    """
    Scheme for verification of POST request body for S3 bucket creation API

    """
    # TODO: The first requirement is length at least of 3 characters. Determine another polices
    #  for buckets names
    bucket_name = fields.Str(required=True, validate=validate.Length(min=3))


@CsmView._app_routes.view("/api/v1/s3/bucket")
class S3BucketListView(CsmView):
    """
    S3 Bucket List View for GET and POST REST API implementation:
        1. Get list of all existing buckets
        2. Create new bucket by given name

    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["s3_bucket_service"]
        self._service_dispatch = {}
        self._s3_session = self.request.session.credentials  # returns a S3Credentials object

    async def get(self):
        """
        GET REST implementation for S3 buckets fetch request

        :return:
        """
        Log.debug(f"Handling list s3 buckets fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        # TODO: in future we can add some parameters for pagination

        return await self._service.list_buckets(self._s3_session)

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

        # NOTE: body is empty
        result = await self._service.create_bucket(self._s3_session, **bucket_creation_body)
        if isinstance(result, Response):
            return result


@CsmView._app_routes.view("/api/v1/s3/bucket/{bucket_name}")
class S3BucketView(CsmView):
    """
    S3 Bucket view for DELETE REST API implementation:
        1. Delete bucket by its given name

    """

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["s3_bucket_service"]
        self._service_dispatch = {}
        self._s3_session = self.request.session.credentials  # returns a S3Credentials object

    async def delete(self):
        """
        DELETE REST implementation for s3 bucket delete request
        :return:
        """
        Log.debug(f"Handling s3 bucket delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        return await self._service.delete_bucket(bucket_name, self._s3_session)


@CsmView._app_routes.view("/api/v1/s3/bucket_policy/{bucket_name}")
class S3BucketPolicyView(CsmView):
    """
    S3 Bucket Policy View for GET, PUT and DELETE REST API implementation:
        1. Get bucket policy of existing bucket
        2. Create or update bucket policy by given bucket name
        3. Delete bucket policy by given bucket name
    """

    def __init__(self, request):
        super(S3BucketPolicyView, self).__init__(request)
        self._service = self.request.app["s3_bucket_service"]
        self._service_dispatch = {}
        self._s3_session = self.request.session.credentials  # returns a S3Credentials object

    """
    GET REST implementation for S3 bucket policy fetch request
    """
    async def get(self):
        Log.debug(f"Handling s3 bucket policy fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        return await self._service.get_bucket_policy(self._s3_session,
                                                     bucket_name)

    """
    PUT REST implementation for S3 bucket policy put request
    """
    async def put(self):
        Log.debug(f"Handling s3 bucket policy put request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        bucket_policy_body = await self.request.json()
        return await self._service.put_bucket_policy(self._s3_session,
                                                     bucket_name,
                                                     bucket_policy_body)

    """
    DELETE REST implementation for s3 bucket policy delete request
    """
    async def delete(self):
        Log.debug(f"Handling s3 bucket policy delete request."
                  f" user_id: {self.request.session.credentials.user_id}")
        bucket_name = self.request.match_info["bucket_name"]
        return await self._service.delete_bucket_policy(self._s3_session,
                                                        bucket_name)
