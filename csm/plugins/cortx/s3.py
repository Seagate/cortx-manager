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

import asyncio
from aiohttp import ClientSession
from boto3.session import Session as Boto3Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config as Boto3Config
from botocore.exceptions import ClientError
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import ssl
from typing import Any, Dict, List, Union
from http import HTTPStatus
import xmltodict
from cortx.utils.log import Log
import json
from csm.common.errors import CsmInternalError, CsmTypeError
from csm.core.blogic import const
from csm.core.data.models.s3 import (S3ConnectionConfig, IamAccount, ExtendedIamAccount,
                                     IamLoginProfile, IamUser, IamUserListResponse,
                                     IamAccountListResponse, IamTempCredentials, IamUserCredentials,
                                     IamAccessKeyMetadata, IamAccessKeysListResponse,
                                     IamAccessKeyLastUsed, IamErrors, IamError)


class BaseClient:
    """
    Base class for IAM API operations.
    """

    def __init__(self, access_key_id: str, secret_access_key: str, config: S3ConnectionConfig,
                 loop=asyncio.get_event_loop(), session_token=None):
        self._loop = loop
        self._executor = ThreadPoolExecutor()
        self._session = Boto3Session(
            aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key,
            aws_session_token=session_token, region_name=const.S3_DEFAULT_REGION)

        resource_name = self.__class__.resource
        use_ssl = config.use_ssl
        scheme = 'https' if use_ssl else 'http'
        self._host = f'{config.host}:{config.port}'
        self._url = f'{scheme}://{self._host}'
        # Path to CA cert is a valid value for 'verify'
        # Allow None for 'verify' if CA cert is not specified
        verify = config.ca_cert_file
        # Create SSL context for HTTP client that handles arbitrary IAM requests
        self._ssl_ctx = ssl.create_default_context(cafile=verify) if verify else False
        boto3_config = None
        if config.max_retries_num:
            retries = {
                'max_attempts': int(config.max_retries_num)
            }
            boto3_config = Boto3Config(retries=retries)
        # Note: use_ssl is ignored if endpoint url is provided with scheme (e.g. https or http)
        self._resource = self._session.resource(
            resource_name, use_ssl=use_ssl,
            verify=verify, endpoint_url=self._url, config=boto3_config
        )

    async def _run_async(self, function):
        return await self._loop.run_in_executor(self._executor, function)

    async def _arbitrary_request(self, action, params, path, verb):
        Log.debug(f"Make query:action:{action}, params:{params}, path:{path}, verb:{verb}")

        headers = const.S3_DEFAULT_REQUEST_HEADERS
        headers['host'] = self._host
        payload = params
        payload['Action'] = action
        aws_request = AWSRequest(method=verb, url='/', data=payload, headers=headers)
        creds = self._session.get_credentials().get_frozen_credentials()
        SigV4Auth(creds, self.__class__.resource, const.S3_DEFAULT_REGION).add_auth(aws_request)
        headers = dict(aws_request.headers)
        # Let all the HTTP client exceptions propagate as is
        async with ClientSession() as http_session:
            async with http_session.request(method=verb, headers=headers, data=payload,
                                            url=self._url, ssl=self._ssl_ctx,
                                            timeout=const.TIMEOUT) as resp:
                status = resp.status
                body = await resp.text()
                parsed_body = xmltodict.parse(
                    body, force_list=const.S3_RESP_LIST_ITEM) if body else {}
                Log.debug('%s responded with %s status', self._host, status)
                return (status, parsed_body)

    def _extract_list(self, path: List[str], resp: dict) -> List[Dict[str, Any]]:
        """
        Extracts a list of items from a parsed S3 server response.

        :param path: a path to the list in the response.
        :param resp: a parsed response from S3 server.
        :return: the list of extracted items (dicts).
        """

        items = resp
        try:
            for key in path:
                items = items[key]
            # The list itself might be None in the response (e.g. <Users/>),
            # convert to [] if that so
            return items[const.S3_RESP_LIST_ITEM] if items is not None else []
        except (TypeError, KeyError):
            log = f"Malformed response from S3 server: expect path {path} in {resp}"
            raise CsmTypeError(log)

    def _create_response(self, cls, data, mapping):
        """
        Creates an instance of type `cls` and fills its fields
        according to mapping
        :returns: an instance of `cls` type
        """

        resp = cls()
        for key in mapping:
            setattr(resp, mapping[key], data[key])

        return resp

    def _create_error(self, status, body) -> IamError:
        """
        Converts a body of a failed query into IamError object
        """
        Log.error(f"Create error body: {body}")
        if 'ErrorResponse' not in body:
            return None

        body = body['ErrorResponse']
        if 'Error' not in body:
            return None

        iam_error = IamError()
        iam_error.http_status = status
        iam_error.error_code = IamErrors(body['Error']['Code'])
        iam_error.error_message = body['Error']['Message']
        return iam_error


class IamClient(BaseClient):
    """
    A management object that alows to perform IAM management operations
    """

    resource = const.S3_RESOURCE_NAME_IAM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.EXT_ACCOUNT_MAPPING = {
            'AccountId': 'account_id',
            'CanonicalId': 'canonical_id',
            'AccountName': 'account_name',
            'AccessKeyId': 'access_key_id',
            'RootSecretKeyId': 'secret_key_id',
            'Status': 'status'
        }

        self.ACCOUNT_MAPPING = {
            'AccountId': 'account_id',
            'CanonicalId': 'canonical_id',
            'AccountName': 'account_name',
            'Email': 'account_email'
        }

        self.LOGIN_PROFILE_MAPPING = {
            'AccountName': 'account_name',
            'PasswordResetRequired': 'password_reset_required',
            'CreateDate': 'create_date'
        }

        self.IAM_USER_MAPPING = {
            'UserName': 'user_name',
            'UserId': 'user_id',
            'Arn': 'arn'
        }

        self.IAM_USER_CREDENTIALS_MAPPING = {
            'UserName': 'user_name',
            'AccessKeyId': 'access_key_id',
            'SecretAccessKey': 'secret_key',
            'Status': 'status'
        }

        self.IAM_ACCESS_KEY_METADATA_MAPPING = {
            'UserName': 'user_name',
            'AccessKeyId': 'access_key_id',
            'Status': 'status',
        }

        self.IAM_ACCESS_KEY_LAST_USED_MAPPING = {
            'Region': 'region',
            'LastUsedDate': 'last_used',
            'ServiceName': 'service_name',
        }

    @Log.trace_method(Log.DEBUG)
    async def create_account(self, account_name: str,
                             account_email: str) -> Union[ExtendedIamAccount, IamError]:
        """
        IAM Account creation. This operation is not present in Amazon IAM API.
        In order to perform this operation, LDAP credentials must be provided into
        the class constructor.

        :returns: ExtendedIamAccount in case of success, IamError otherwise
        """
        Log.debug(f"Create account profile. account_name:{account_name}, "
                  f"account_email:{account_email}")
        params = {
            'AccountName': account_name,
            'Email': account_email
        }

        (code, body) = await self._arbitrary_request('CreateAccount', params, '/', 'POST')
        Log.debug(f"Create account profile status: {code}")
        if code != 201:
            return self._create_error(code, body)
        else:
            account = body['CreateAccountResponse']['CreateAccountResult']['Account']
            resp = self._create_response(ExtendedIamAccount, account, self.EXT_ACCOUNT_MAPPING)

            # For some strange reason there is no email field in the server response
            resp.account_email = account_email
            return resp

    @Log.trace_method(Log.DEBUG, exclude_args=['account_password'])
    async def create_account_login_profile(self, account_name, account_password,
                                           require_reset=False) -> Union[IamLoginProfile, IamError]:
        """
        Login profile creation.
        Note that it is required to provide S3 account credentials, not LDAP ones.

        :returns: IamLoginProfile in case of success, IamError otherwise
        """
        Log.debug(f"Create account login profile. account_name:{account_name}, "
                  f"require_reset:{require_reset}")
        params = {
            'AccountName': account_name,
            'Password': account_password,
            'PasswordResetRequired': require_reset
        }

        (code, body) = await self._arbitrary_request(
            'CreateAccountLoginProfile', params, '/', 'POST')
        Log.debug(f"Create login profile status: {code}")
        if code != 201:
            return self._create_error(code, body)
        else:
            profile = body['CreateAccountLoginProfileResponse']['CreateAccountLoginProfileResult']
            profile = profile['LoginProfile']
            return self._create_response(IamLoginProfile, profile, self.LOGIN_PROFILE_MAPPING)

    @Log.trace_method(Log.DEBUG, exclude_args=['account_password'])
    async def update_account_login_profile(self, account_name, account_password,
                                           require_reset=False) -> Union[bool, IamError]:
        """
        Login profile update.
        Note that it is required to provide S3 account credentials, not LDAP ones.

        :returns: True in case of success, IamError otherwise
        """
        Log.debug(f"Update account login profile: account_name:{account_name}, "
                  f"require_reset:{require_reset}")

        params = {
            'AccountName': account_name,
            'Password': account_password,
            'PasswordResetRequired': require_reset
        }

        (code, body) = await self._arbitrary_request(
            'UpdateAccountLoginProfile', params, '/', 'POST')
        Log.debug(f"Update account profile status: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def list_account_login_profiles(self, account_name) -> Union[bool, IamError]:
        """
        Login profile update.
        Note that it is required to provide S3 account credentials, not LDAP ones.

        :returns: True in case of success, IamError otherwise
        """
        Log.debug(f"List account login profile. account_name:{account_name}")
        params = {
            'AccountName': account_name
        }

        (code, body) = await self._arbitrary_request('GetAccountLoginProfile', params, '/', 'POST')
        Log.debug(f"List account profile status: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def get_account(self, account_name) -> Union[IamAccount, IamError]:
        accounts = await self.list_accounts()
        if isinstance(accounts, IamError):
            return accounts
        for acc in accounts.iam_accounts:
            if acc.account_name == account_name:
                return acc
        return None

    @Log.trace_method(Log.DEBUG)
    async def list_accounts(self, max_items=None,
                            marker=None) -> Union[IamAccountListResponse, IamError]:
        """
        Fetches the list of S3 accounts from the IAM server.
        Note that max_items and marker parameters are not supported yet!

        :returns: IamAccountListResponse or IamError
        """
        Log.debug(f"List account status. max_items:{max_items}, marker:{marker}")
        params = {}

        if marker:
            params['Marker'] = marker

        if max_items:
            params['MaxItems'] = max_items

        (code, body) = await self._arbitrary_request('ListAccounts', params, '/', 'POST')
        Log.debug(f"List account status: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            users = self._extract_list(
                ['ListAccountsResponse', 'ListAccountsResult', 'Accounts'], body)
            converted_accounts = []
            for raw_user in users:
                converted_accounts.append(self._create_response(IamAccount, raw_user,
                                                                self.ACCOUNT_MAPPING))

            resp = IamAccountListResponse()
            resp.iam_accounts = converted_accounts
            raw = body['ListAccountsResponse']['ListAccountsResult']['IsTruncated']

            resp.is_truncated = raw == 'true'
            if resp.is_truncated:
                resp.marker = body['ListAccountsResponse']['ListAccountsResult']['Marker']

            return resp

    @Log.trace_method(Log.DEBUG)
    async def reset_account_access_key(self, account_name) -> Union[ExtendedIamAccount, IamError]:
        """
        Reset access and secret key

        :returns: ExtendedIamAccount in case of success, IamError otherwise
        """
        Log.debug(f"Reset account access key. account_name:{account_name}")
        params = {
            'AccountName': account_name
        }

        (code, body) = await self._arbitrary_request('ResetAccountAccessKey', params, '/', 'POST')
        Log.debug(f"Reset account access key status code: {code}")
        if code != 201:
            return self._create_error(code, body)
        else:
            result = body['ResetAccountAccessKeyResponse']['ResetAccountAccessKeyResult']
            resp = self._create_response(ExtendedIamAccount, result['Account'],
                self.EXT_ACCOUNT_MAPPING)

            # TODO: find out why there is no email the response
            return resp

    @Log.trace_method(Log.DEBUG)
    async def delete_account(self, account_name, force=False) -> Union[bool, IamError]:
        """
        Note that in order to delete account_name we need to use access key
        and secret key of account_name

        :returns: True in case of success, IamError in case of problem
        """
        Log.debug(f"Delete account access key: account_name:{account_name}, "
                  f"force:{force}")
        params = {
            'AccountName': account_name
        }

        if force:
            params['Force'] = True

        (code, body) = await self._arbitrary_request('DeleteAccount', params, '/', 'POST')
        Log.debug(f"Delete account status code: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def create_user(self, user_name) -> Union[IamUser, IamError]:
        """
        Create an IAM user.

        :returns: IamUser in case of success, IamError otherwise
        """
        Log.debug(f"Create iam user. user_name:{user_name}")
        params = {
            'UserName': user_name
        }

        (code, body) = await self._arbitrary_request('CreateUser', params, '/', 'POST')
        Log.debug(f"Create iam user status code: {code}")
        if code != 201:
            return self._create_error(code, body)
        else:
            user = body['CreateUserResponse']['CreateUserResult']['User']
            return self._create_response(IamUser, user, self.IAM_USER_MAPPING)

    @Log.trace_method(Log.DEBUG, exclude_args=['user_password'])
    async def create_user_login_profile(self, user_name, user_password, require_reset=False):
        # TODO: server returns OperationNotSupported. Why??
        Log.debug(f"Create user login profile. user_name:{user_name}, "
                  f"require_reset:{require_reset}")
        params = {
            'UserName': user_name,
            'Password': user_password,
            'PasswordResetRequired': require_reset
        }

        (code, body) = await self._arbitrary_request('CreateLoginProfile', params, '/', 'POST')
        Log.debug(f"Create user profile status code: {code}")
        if code != 201:
            return self._create_error(code, body)
        else:
            return None

    @Log.trace_method(Log.DEBUG, exclude_args=['user_password'])
    async def update_user_login_profile(self, user_name, user_password,
                                        require_reset=False) -> Union[bool, IamError]:
        """
        User's login profile update.
        Note that it is required to provide S3 account credentials.

        :returns: True in case of success, IamError otherwise
        """
        Log.debug(f"Update user login profile: user_name:{user_name}, "
                  f"require_reset:{require_reset}")

        params = {
            'UserName': user_name,
            'Password': user_password,
            'PasswordResetRequired': require_reset
        }

        (code, body) = await self._arbitrary_request('UpdateLoginProfile', params, '/', 'POST')
        Log.debug(f"Update user profile status: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def list_users(self, marker=None,
                         max_items=None) -> Union[IamUserListResponse, IamError]:
        """
        Note that max_items and marker are not working for now!!

        :returns: IamUserListResponse in case of success, IamError otherwise
        """
        Log.debug(f"List iam user. marker:{marker}, "
                  f"max_items:{max_items}")
        params = {}

        if marker:
            params['Marker'] = marker

        if max_items:
            params['MaxItems'] = max_items

        (code, body) = await self._arbitrary_request('ListUsers', params, '/', 'POST')
        Log.debug(f"List iam User status code: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            users = self._extract_list(['ListUsersResponse', 'ListUsersResult', 'Users'], body)
            converted_users = []
            for raw in users:
                converted_users.append(self._create_response(IamUser, raw, self.IAM_USER_MAPPING))

            resp = IamUserListResponse()
            resp.iam_users = converted_users
            raw = body['ListUsersResponse']['ListUsersResult']['IsTruncated']

            resp.is_truncated = raw == 'true'
            if resp.is_truncated:
                resp.marker = body['ListUsersResponse']['ListUsersResult']['Marker']

            return resp

    @Log.trace_method(Log.DEBUG)
    async def delete_user(self, user_name) -> Union[bool, IamError]:
        """
        IAM user deletion.
        :returns: True in case of success, IamError in case of problem
        """
        Log.debug(f"Delete iam User: {user_name}")
        params = {
            'UserName': user_name
        }

        (code, body) = await self._arbitrary_request('DeleteUser', params, '/', 'POST')
        Log.debug(f"Delete iam User status code: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def get_user(self, user_name) -> Union[IamUser, IamError]:
        """
        Queries a single IAM user.

        TODO: Currently is not supported by our IAM server.
        :returns: IamUser in case of success, IamError in case of problem
        """
        raise NotImplementedError()

        params = {
            'UserName': user_name
        }

        (code, body) = await self._arbitrary_request('GetUser', params, '/', 'POST')
        if code != 200:
            return self._create_error(code, body)
        else:
            return None

    @Log.trace_method(Log.DEBUG)
    async def update_user(self, user_name,
                          new_user_name=None) -> Union[bool, IamError]:
        """
        Update an existing IAM user.

        :param user_name: TODO: find out details about this field
        :param new_user_name: If not None, user will be renamed accordingly
        :returns: True in case of success, IamError in case of problem
        """
        Log.debug(f"Update iam User: {user_name} "
                  f"new_user_name:{new_user_name}")
        params = {
            'UserName': user_name
        }

        if new_user_name:
            params['NewUserName'] = new_user_name

        (code, body) = await self._arbitrary_request('UpdateUser', params, '/', 'POST')
        Log.debug(f"Update iam User status code: {code}")
        if code != 200:
            return self._create_error(code, body)
        else:
            # TODO: our IAM server does not return the updated user information
            return True

    async def create_user_access_key(self, user_name=None) -> Union[ExtendedIamAccount, IamError]:
        """
        Creates an access key id and secret key for IAM user.

        :param user_name: IAM user name, if None, user is deduced from the current session
        :returns: credentials in case of success, IamError in case of problem
        """

        Log.audit(f"Create access key for user: {user_name}")
        params = {}
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(const.S3_IAM_CMD_CREATE_ACCESS_KEY,
                                              params, '/', 'POST')
        Log.audit(f"Create access key status code: {code}")
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            creds = body[const.S3_IAM_CMD_CREATE_ACCESS_KEY_RESP][
                            const.S3_IAM_CMD_CREATE_ACCESS_KEY_RESULT][
                                const.S3_PARAM_ACCESS_KEY]
            return self._create_response(IamUserCredentials, creds,
                                         self.IAM_USER_CREDENTIALS_MAPPING)

    async def update_user_access_key(self, access_key_id, status, user_name=None) -> bool:
        """
        Updates an access key status (active/inactive) for IAM user.

        :param user_name: IAM user name, if None, user is deduced from the current session
        :param access_key_id: access key ID
        :param status: new active key status (Active/inactive)
        :returns: true in case of success, IamError in case of problem
        """

        Log.audit(f"Update access key {access_key_id} for user: {user_name}"
                  f" with status {status}")
        params = {
            'AccessKeyId': access_key_id,
            'Status': status
        }
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(const.S3_IAM_CMD_UPDATE_ACCESS_KEY,
                                              params, '/', 'POST')
        Log.audit(f"Update access key status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    async def get_user_access_key_last_used(self, access_key_id,
                                            user_name=None) -> Union[IamAccessKeyLastUsed, IamError]:
        """
        Retrieves the timestamp of the last access key usage.

        :param access_key_id: access key ID
        :param user_name: IAM user name, if None, user is deduced from the current session
        :returns: timestamp in case of success, IamError in case of problem
        """
        Log.audit(f"Get last used time of IAM user's {user_name} access key {access_key_id}")
        params = {
            'AccessKeyId': access_key_id
        }
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(const.S3_IAM_CMD_GET_ACCESS_KEY_LAST_USED,
                                              params, '/', 'POST')
        Log.audit(f"Update access key status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            info = body[const.S3_IAM_CMD_GET_ACCESS_KEY_LAST_USED_RESP][
                const.S3_IAM_CMD_GET_ACCESS_KEY_LAST_USED_RESULT][
                    const.S3_PARAM_ACCESS_KEY_LAST_USED]
            return self._create_response(IamAccessKeyLastUsed, info,
                                         self.IAM_ACCESS_KEY_LAST_USED_MAPPING)

    async def list_user_access_keys(self, user_name=None, marker=None,
                                    max_items=None) -> Union[IamAccessKeysListResponse, IamError]:
        """
        Gets the list of access keys for IAM user
        Note that max_items and marker are not working for now!!

        :param user_name: IAM user name, if None, user is deduced from the current session
        :param marker: pagination marker from the previous response
        :param max_items: maximum number of access keys to return in single response
        :returns: IamAccessKeysListResponse in case of success, IamError otherwise
        """
        Log.audit(f"List IAM user's {user_name} access keys. marker: {marker},"
                  f" max_items: {max_items}")
        params = {}
        if user_name is not None:
            params[const.S3_PARAM_USER_NAME] = user_name

        if marker:
            params[const.S3_PARAM_MARKER] = marker

        if max_items:
            params[const.S3_PARAM_MAX_ITEMS] = max_items

        (code, body) = await self._arbitrary_request(
            const.S3_IAM_CMD_LIST_ACCESS_KEYS, params, '/', 'POST')
        Log.audit(f"List IAM user's access keys status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            keys = self._extract_list(
                [const.S3_IAM_CMD_LIST_ACCESS_KEYS_RESP,
                 const.S3_IAM_CMD_LIST_ACCESS_KEYS_RESULT,
                 const.S3_PARAM_ACCESS_KEY_METADATA],
                body)
            converted_keys = []
            for raw in keys:
                converted_keys.append(self._create_response(IamAccessKeyMetadata, raw,
                                      self.IAM_ACCESS_KEY_METADATA_MAPPING))

            resp = IamAccessKeysListResponse()
            resp.access_keys = converted_keys
            raw = body[const.S3_IAM_CMD_LIST_ACCESS_KEYS_RESP][
                            const.S3_IAM_CMD_LIST_ACCESS_KEYS_RESULT][
                                const.S3_PARAM_IS_TRUNCATED]

            resp.is_truncated = raw == 'true'
            if resp.is_truncated:
                resp.marker = body[const.S3_IAM_CMD_LIST_ACCESS_KEYS_RESP][
                                        const.S3_IAM_CMD_LIST_ACCESS_KEYS_RESULT][
                                            const.S3_PARAM_MARKER]

            return resp

    async def delete_user_access_key(self, access_key_id, user_name=None) -> Union[bool, IamError]:
        """
        Deletes an access key for IAM user.

        :param user_name: IAM user name, if None, user is deduced from the current session
        :param access_key_id: ID of the access key to be deleted
        :returns: true in case of success, IamError in case of problem
        """

        Log.audit(f"Delete access key {access_key_id} for IAM user {user_name}")
        params = {
            'AccessKeyId': access_key_id
        }
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(const.S3_IAM_CMD_DELETE_ACCESS_KEY, params,
                                              '/', 'POST')
        Log.debug(f"Delete iam User status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True


class S3Client(BaseClient):
    """
    Class represents S3 server connection that manages buckets
    """

    resource = const.S3_RESOURCE_NAME_S3

    @Log.trace_method(Log.DEBUG)
    async def create_bucket(self, bucket_name):
        """
        Create a S3 bucket using credentials passed during client creation.

        :returns: S3.Bucket
        """
        Log.debug(f"create bucket: {bucket_name}")
        return await self._loop.run_in_executor(self._executor,
                                                partial(self._resource.create_bucket,
                                                        Bucket=bucket_name))

    @Log.trace_method(Log.DEBUG)
    async def get_bucket(self, bucket_name):
        """
        Checks if a bucket with a specified name exists and returns it
        """
        Log.debug(f"get bucket: {bucket_name}")
        bucket = self._resource.Bucket(bucket_name)
        try:
            coro = partial(self._resource.meta.client.head_bucket, Bucket=bucket_name)
            await self._loop.run_in_executor(self._executor, coro)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                bucket = None
            else:
                raise e

        return bucket

    @Log.trace_method(Log.DEBUG)
    async def delete_bucket(self, bucket_name: str):
        Log.debug(f"delete bucket: {bucket_name}")
        bucket = await self._loop.run_in_executor(self._executor, self._resource.Bucket, bucket_name)
        # Assume that the bucket is empty, if not, the error will be returned.
        # It is user's responsibility to empty the bucket before the deletion.
        await self._loop.run_in_executor(self._executor, bucket.delete)

    @Log.trace_method(Log.DEBUG)
    async def get_all_buckets(self):
        Log.debug(f"Get all buckets ")
        return await self._loop.run_in_executor(self._executor, self._resource.buckets.all)

    @Log.trace_method(Log.DEBUG)
    async def get_bucket_tagging(self, bucket_name: str):
        # When the tag_set is not available ClientError is raised
        # Need to avoid that in order to iterate over tags for all available buckets
        Log.debug(f"Get bucket tagging: {bucket_name}")
        def _run():
            try:
                tagging = self._resource.BucketTagging(bucket_name)
                tag_set = {tag['Key'] : tag['Value'] for tag in tagging.tag_set}
            except ClientError:
                tag_set = {}
            return tag_set
        return await self._loop.run_in_executor(self._executor, _run)

    @Log.trace_method(Log.DEBUG)
    async def put_bucket_tagging(self, bucket_name, tags: dict):
        Log.debug(f"Put bucket tagging: bucket_name:{bucket_name}, tags:{tags}")
        def _run():
            tag_set = {
                'TagSet': [
                    {
                        'Key': key,
                        'Value': tags[key]
                    } for key in tags
                ]
            }
            tagging = self._resource.BucketTagging(bucket_name)
            return tagging.put(Tagging=tag_set)
        return await self._loop.run_in_executor(self._executor, _run)

    @Log.trace_method(Log.DEBUG)
    async def get_bucket_policy(self, bucket_name: str):
        """
        Fetch s3 bucket policy by given bucket details.

        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :returns: A dict of bucket policy
        """
        Log.debug(f"Get bucket tagging: {bucket_name}")
        def _run():
            bucket = self._resource.BucketPolicy(bucket_name)
            return json.loads(bucket.policy)

        return await self._loop.run_in_executor(self._executor, _run)

    @Log.trace_method(Log.DEBUG)
    async def put_bucket_policy(self, bucket_name: str, policy: dict):
        """
        Create or update s3 bucket policy for given bucket details.

        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :param policy: s3 bucket name
        :type policy: dict
        :returns:
        """
        Log.debug(f"Put bucket tagging: bucket_name: {bucket_name}, policy: {policy}")
        def _run():
            bucket = self._resource.BucketPolicy(bucket_name)
            bucket_policy = json.dumps(policy)
            return bucket.put(Bucket=bucket_name, Policy=bucket_policy)

        return await self._loop.run_in_executor(self._executor, _run)

    @Log.trace_method(Log.DEBUG)
    async def delete_bucket_policy(self, bucket_name: str):
        """
        Delete s3 bucket policy by given bucket details.

        :param bucket_name: s3 bucket name
        :type bucket_name: str
        :returns:
        """

        Log.debug(f"Delete bucket tagging: {bucket_name}")
        bucket = await self._loop.run_in_executor(self._executor,
                                                  self._resource.BucketPolicy,
                                                  bucket_name)
        return await self._loop.run_in_executor(self._executor, bucket.delete)


class S3Plugin:
    """
    Plugin that provides IAM-related operations implementation.

    The plugin requires an S3ConnectionConfig instance that contains the necessary
    information for IAM server access.

    Steps to use this plugin for IAM Account management:
    1. Prepare root IAM server LDAP credentials
    2. Call s3plugin.get_iam_client('ldap_login', 'ldap_password', connection_config)
       to retrieve the corresponding management object
    3. Perform API queries using that object

    Example:
        client = s3plugin.get_iam_client('ldap_login', 'ldap_pwd', connection_config)
        account_list = await client.list_accounts()

    A similar sequence of steps is required for IAM User management.
    1. Prepare access and secret key of the account on behalf of which you are going to
       manage IAM Users
    2. Call s3plugin.get_iam_client('access_key', 'secret_ey', connection_config)
       to retrieve the corresponding management object
    3. Perform API queries using that object

    In order to authenticate via some Login Profile it is sufficient to only call
    the get_temp_credentials function, e.g.
        creds = await s3plugin.get_temp_credentials('login', 'pwd', connection_config=config)
    """
    def __init__(self):
        Log.info('S3 plugin is loaded')

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key','secret_key','session_token'])
    def get_iam_client(self, access_key, secret_key, connection_config=None, session_token=None) -> IamClient:
        """
        Returns a management object for S3/IAM accounts.
        """
        if not connection_config:
            raise CsmInternalError('Connection configuration must be provided')

        return IamClient(access_key, secret_key, connection_config,
                         asyncio.get_event_loop(), session_token)

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key','secret_key','session_token'])
    def get_s3_client(self, access_key, secret_key, connection_config=None, session_token=None) -> S3Client:
        """
        Returns a management object for S3/IAM accounts.
        """
        if not connection_config:
            raise CsmInternalError('Connection configuration must be provided')

        return S3Client(access_key, secret_key, connection_config,
                        asyncio.get_event_loop(), session_token)


    @Log.trace_method(Log.DEBUG, exclude_args=['password'])
    async def get_temp_credentials(self, account_name, password, duration=None,
                                   user_name=None, connection_config=None):
        """
        Authentication via some Login Profile
        :param account_name:
        :param password:
        :param duration: Session expiry time (in seconds). If set, it must be
                         greater than 900.
        :param user_name: TODO: find out details about this field
        :param connection_config: TODO: find out details about this field
        :returns: An instance of IamTempCredentials object
        """
        Log.debug(f"Get temp credentials: {account_name}, user_name:{user_name}")
        iamcli = IamClient('', '', connection_config, asyncio.get_event_loop())
        params = {
            'AccountName': account_name,
            'Password': password
        }

        if duration:
            params['Duration'] = duration
        if user_name:
            params['UserName'] = user_name

        (code, body) = await iamcli._arbitrary_request('GetTempAuthCredentials', params, '/', 'POST')
        if code != 201:
            return iamcli._create_error(code, body)
        else:
            creds = body['GetTempAuthCredentialsResponse']['GetTempAuthCredentialsResult']
            return iamcli._create_response(IamTempCredentials, creds['AccessKey'], {
                'UserName': 'user_name',
                'AccessKeyId': 'access_key',
                'SecretAccessKey': 'secret_key',
                'Status': 'status',
                'ExpiryTime': 'expiry_time',
                'SessionToken': 'session_token'
            })
