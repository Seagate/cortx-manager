#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          access_keys.py
 Description:       Service for S3 access keys management

 Creation Date:     08/18/2020
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


from cortx.utils.log import Log
from csm.core.data.models.s3 import IamError
from csm.core.services.s3.utils import S3BaseService, CsmS3ConfigurationFactory


class S3AccessKeysService(S3BaseService):
    """
    Service for S3 access keys management
    """
    def __init__(self, s3_plugin):
        self._s3_plugin = s3_plugin
        self._iam_connection_config = CsmS3ConfigurationFactory.get_iam_connection_config()

    def _fetch_iam_client(self, s3_session):
        """
        Creates IAM client for the current S3 session credentials

        :param s3_session: S3 session object
        :returns: IAM client object
        """
        return self._s3_plugin.get_iam_client(s3_session.access_key, s3_session.secret_key,
                                              self._iam_connection_config, s3_session.session_token)

    @Log.trace_method(Log.DEBUG)
    async def create_access_key(self, s3_session, user_name=None):
        """
        Creates an S3 access key for the provided user

        :param s3_session: S3 session object
        :returns: a dictionary with details about the new access key
        """
        Log.debug('Creating an access key')
        iam_client = self._fetch_iam_client(s3_session)
        resp = await iam_client.create_user_access_key(user_name=user_name)
        if isinstance(resp, IamError):
            self._handle_error(resp)
        return vars(resp)

    @Log.trace_method(Log.DEBUG)
    async def update_access_key(self, s3_session, access_key_id, status, user_name=None):
        """
        Updates the status of the provided access key

        :param s3_session: S3 session object
        :returns: a dictionary with details about the updated access key
        """
        Log.debug(f'Updating the access key {access_key_id} with status {status}')
        iam_client = self._fetch_iam_client(s3_session)
        resp = await iam_client.update_user_access_key(access_key_id, status, user_name=user_name)
        if isinstance(resp, IamError):
            self._handle_error(resp)
        return {
            "access_key_id": access_key_id,
            "status": status
        }

    @Log.trace_method(Log.DEBUG)
    async def list_access_keys(self, s3_session, user_name=None, marker=None, limit=None):
        """
        Fetches a list of provided IAM user's access keys

        :param s3_session: S3 session object
        :param marker: continuation marker from the previous list access keys operation
        :param limit: the maximum number of entities to return
        :returns: a dictionary with access keys and continuation marker (if the list's limited)
        """
        Log.debug(f'Listing access keys, marker {marker}, limit {limit}')
        iam_client = self._fetch_iam_client(s3_session)
        access_keys_resp = await iam_client.list_user_access_keys(
            user_name=user_name, marker=marker, max_items=limit)
        if isinstance(access_keys_resp, IamError):
            self._handle_error(access_keys_resp)
        resp_keys = []
        for key in access_keys_resp.access_keys:
            resp_keys.append(
                {
                    "user_name": key.user_name,
                    "access_key_id": key.access_key_id,
                    "status": key.status
                }
            )
        resp = {'access_keys': resp_keys}
        if access_keys_resp.is_truncated:
            resp['continue'] = access_keys_resp.marker
        return resp

    @Log.trace_method(Log.DEBUG)
    async def delete_access_key(self, s3_session, access_key_id, user_name=None):
        """
        Deletes the provided access key

        :param s3_session: S3 session object
        :param access_key_id: access key ID
        :returns: a dictionary containing a message about the deletion status
        """
        Log.debug(f'Deleting access key {access_key_id}')
        iam_client = self._fetch_iam_client(s3_session)
        resp = await iam_client.delete_user_access_key(access_key_id, user_name=user_name)
        if isinstance(resp, IamError):
            self._handle_error(resp)
        return {
            "message": f"Access key {access_key_id} was successfully deleted"
        }
