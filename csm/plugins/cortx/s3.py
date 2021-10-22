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
import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config as Boto3Config
from botocore.credentials import ReadOnlyCredentials
from botocore.exceptions import ClientError
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import ssl
from typing import Any, Callable, Dict, List, Tuple, Optional, Union
from http import HTTPStatus
import xmltodict
from cortx.utils.log import Log
from csm.common.errors import CsmInternalError, CsmTypeError, CsmResourceNotAvailable
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

    def __init__(
        self, access_key_id: str, secret_access_key: str, config: S3ConnectionConfig,
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(), session_token: str = None
    ) -> None:
        """
        Initialize the BaseClient.

        :param access_key_id: access key ID or LDAP admin user name.
        :param secret_access_key: secret access key or LDAP admin password.
        :param config: object with client's configuration.
        :param loop: event loop to run asynchronous calls.
        :param session_token: session token.
        :returns: None.
        """

        self._loop = loop
        self._executor = ThreadPoolExecutor()
        # Empty credentials are possible for the "get temporary credentials" operation
        if access_key_id and secret_access_key:
            self._creds = ReadOnlyCredentials(access_key_id, secret_access_key, session_token)
        else:
            self._creds = None
        use_ssl = config.use_ssl
        scheme = 'https' if use_ssl else 'http'
        self._host = f'{config.host}:{config.port}'
        self._url = f'{scheme}://{self._host}'
        # Path to CA cert is a valid value for 'verify'
        # Allow None for 'verify' if CA cert is not specified
        verify = config.ca_cert_file
        # Create SSL context for HTTP client that handles arbitrary IAM requests
        self._ssl_ctx = ssl.create_default_context(cafile=verify) if verify else False
        # Do not create high-level resource if credentials are not available
        if self._creds:
            boto3_config = None
            if config.max_retries_num:
                retries = {
                    'max_attempts': int(config.max_retries_num)
                }
                boto3_config = Boto3Config(retries=retries)
            resource_name = self.__class__.resource
            # Note: use_ssl is ignored if endpoint url is provided with scheme (e.g. https or http)
            self._resource = boto3.resource(
                resource_name, aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key, aws_session_token=session_token,
                use_ssl=use_ssl, region_name=const.S3_DEFAULT_REGION,
                verify=verify, endpoint_url=self._url, config=boto3_config
            )

    async def _run_async(self, function: Callable[..., Any]) -> Any:
        """
        Runs the provided function asynchronously.

        :param function: a function to run.
        """
        return await self._loop.run_in_executor(self._executor, function)

    async def http_request(
        self, headers: Optional[Dict[str, str]], payload: Any, path: str, verb: str
    ) -> Tuple[HTTPStatus, Optional[str]]:
        """
        Make HTTP request to S3 server.

        :param headers: HTTP headers.
        :param params: request body in JSON.
        :param path: request URI.
        :param verb: request method.
        :returns: HTTP code and the response payload as a text.
        """

        Log.debug(f"Make HTTP request: headers {headers}, payload: {payload},"
                  f" path {path}, verb {verb}")

        # Let all the HTTP client exceptions propagate as is
        async with ClientSession() as http_session:
            async with http_session.request(method=verb, headers=headers, data=payload,
                                            url=self._url + path, ssl=self._ssl_ctx,
                                            timeout=const.TIMEOUT) as resp:
                status = resp.status
                body = await resp.text()
                return status, body

    async def _arbitrary_request(
        self, action: str, params: Dict[str, Any], path: str, verb: str
    ) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Make signed arbitrary request to S3 server.

        :param action: S3/IAM server operation (e.g. CreateAccount).
        :param params: JSON parameters for the request.
        :param path: URI to send the request to.
        :param verb: HTTP method.
        :returns: HTTP status code and parsed response's body as a dict
        """

        Log.debug(f"Make query:action:{action}, params:{params}, path:{path}, verb:{verb}")

        headers = const.S3_DEFAULT_REQUEST_HEADERS
        headers['host'] = self._host
        payload = params
        payload['Action'] = action

        if self._creds:
            aws_request = AWSRequest(method=verb, url=path, data=payload, headers=headers)
            SigV4Auth(
                self._creds, self.__class__.resource, const.S3_DEFAULT_REGION).add_auth(aws_request)
            headers = dict(aws_request.headers)

        status, body = await self.http_request(headers, payload, path, verb)
        Log.debug(f'{self._host} responded with {status}')
        parsed_body = xmltodict.parse(
            body, force_list=const.S3_RESP_LIST_ITEM) if body else {}
        return (status, parsed_body)

    def _extract_element(
        self, path: Tuple[str], resp: Dict[str, Any], is_list: bool = False
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extracts an item from a parsed S3 server response.

        :param path: a path (tuple of keys) to the list in the response.
        :param resp: a parsed response (OrderedDict) from S3 server.
        :param is_list: flag if the exracted item is list.
        :return: the extracted item (either text, dict or list).
        """

        element = resp
        try:
            for key in path:
                element = element[key]
            # The actual list in XML parser output is stored under the key
            # that denotes a single list item, e.g. 'member' or 'item'.
            # The list might be None if no list items were in original XML (e.g. <Users/> case)
            # convert to [] if that so
            if is_list:
                return element[const.S3_RESP_LIST_ITEM] if element is not None else []
            else:
                return element
        except (TypeError, KeyError):
            log = f"Malformed response from S3 server: expect path {path} in {resp}"
            raise CsmTypeError(log)

    def _create_response(self, cls, data: Dict[str, Any], mapping: Dict[str, str]) -> Any:
        """
        Creates an instance of type `cls` and fills its fields according to mapping.
        :param cls: model's class object.
        :param data: dict with values.
        :param mapping: dict that maps data values to model's attributes.
        :returns: an instance of `cls` type
        """

        resp = cls()
        for key in mapping:
            setattr(resp, mapping[key], data[key])

        return resp

    def _create_error(self, status: HTTPStatus, body: str) -> IamError:
        """
        Converts a body of a failed query into IamError object.

        :param status: HTTP Status code.
        :param body: parsed HTTP response (dict) with the error's decription.
        :returns: instance of IamError.
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

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes the IamClient
        """

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

        self.IAM_GET_TMP_CREDS_MAPPING = {
            'UserName': 'user_name',
            'AccessKeyId': 'access_key',
            'SecretAccessKey': 'secret_key',
            'Status': 'status',
            'ExpiryTime': 'expiry_time',
            'SessionToken': 'session_token'
        }

    @Log.trace_method(Log.DEBUG)
    async def create_account(
        self, account_name: str, account_email: str,\
        access_key: str, secret_key: str
    ) -> Union[ExtendedIamAccount, IamError]:
        """
        Create IAM account.

        This operation is not present in Amazon IAM API.
        In order to perform this operation, LDAP credentials must be provided into
        the class constructor.

        :param account_name: account's name.
        :param account_email: account's email.
        :param access_key: user provided account's access_key.
        :param secret_key: user provided account's secret_key.
        :returns: ExtendedIamAccount in case of success, IamError otherwise
        """

        Log.debug(f"Create account profile. account_name:{account_name}, "
                  f"account_email:{account_email}")
        params = {
            'AccountName': account_name,
            'Email': account_email
        }

        if access_key is not None and secret_key is not None:
            params['AccessKey'] = access_key
            params['SecretKey'] = secret_key

        (code, body) = await self._arbitrary_request('CreateAccount', params, '/', 'POST')
        Log.debug(f"Create account profile status: {code}")
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            account = self._extract_element(const.S3_CREATE_ACCOUNT_RESP_ACCOUNT_PATH, body)
            resp = self._create_response(ExtendedIamAccount, account, self.EXT_ACCOUNT_MAPPING)

            # For some strange reason there is no email field in the server response
            resp.account_email = account_email
            return resp

    @Log.trace_method(Log.DEBUG, exclude_args=['account_password'])
    async def create_account_login_profile(
        self, account_name: str, account_password: str, require_reset: bool = False
    ) -> Union[IamLoginProfile, IamError]:
        """
        Create account login profile.

        Note that it is required to provide S3 account credentials, not LDAP ones.

        :param account name: account's name.
        :param account_password: account's password.
        :param require_reset: flag if the user needs to reset the password once logged in.
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
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            profile = self._extract_element(
                const.S3_CREATE_ACCOUNT_LOGIN_PROFILE_RESP_PROFILE_PATH, body)
            return self._create_response(IamLoginProfile, profile, self.LOGIN_PROFILE_MAPPING)

    @Log.trace_method(Log.DEBUG, exclude_args=['account_password'])
    async def update_account_login_profile(
        self, account_name: str, account_password: str, require_reset: bool = False
    ) -> Union[bool, IamError]:
        """
        Update account login profile.

        Note that it is required to provide S3 account credentials, not LDAP ones.

        :param account name: account's name.
        :param account_password: account's password.
        :param require_reset: flag if the user needs to reset the password once logged in.
        :returns: True in case of success, IamError otherwise.
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
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def list_account_login_profiles(self, account_name: str) -> Union[bool, IamError]:
        """
        List account login profile.

        Note that it is required to provide S3 account credentials, not LDAP ones.

        :param account_name: account's name.
        :returns: True in case of success, IamError otherwise
        """

        Log.debug(f"List account login profile. account_name:{account_name}")
        params = {
            'AccountName': account_name
        }

        (code, body) = await self._arbitrary_request('GetAccountLoginProfile', params, '/', 'POST')
        Log.debug(f"List account profile status: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def get_account(self, account_name: str) -> Union[Optional[IamAccount], IamError]:
        """
        Get IAM account.

        :param account_name: account's name
        :return account object if the account exists, None if not, IamError in case of error.
        """

        accounts = await self.list_accounts()
        if isinstance(accounts, IamError):
            return accounts
        for acc in accounts.iam_accounts:
            if acc.account_name == account_name:
                return acc
        return None

    @Log.trace_method(Log.DEBUG)
    async def list_accounts(
        self, max_items: Optional[int] = None, marker: Optional[str] = None
    ) -> Union[IamAccountListResponse, IamError]:
        """
        Fetches the list of S3 accounts from the IAM server.

        Note that max_items and marker parameters are not supported yet!

        :param max_items: maximum number of items to return.
        :param marker: pagination marker.
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
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            users = self._extract_element(
                const.S3_LIST_ACCOUNTS_RESP_ACCOUNTS_PATH, body, is_list=True)
            converted_accounts = []
            for raw_user in users:
                converted_accounts.append(self._create_response(IamAccount, raw_user,
                                                                self.ACCOUNT_MAPPING))

            resp = IamAccountListResponse()
            resp.iam_accounts = converted_accounts
            raw = self._extract_element(const.S3_LIST_ACCOUNTS_RESP_ISTRUNCATED_PATH, body)

            resp.is_truncated = raw == 'true'
            if resp.is_truncated:
                resp.marker = self._extract_element(const.S3_LIST_ACCOUNTS_RESP_MARKER_PATH, body)

            return resp

    @Log.trace_method(Log.DEBUG)
    async def reset_account_access_key(
        self, account_name: str
    ) -> Union[ExtendedIamAccount, IamError]:
        """
        Reset access and secret key.

        :param account_name: account's name.
        :returns: ExtendedIamAccount in case of success, IamError otherwise.
        """

        Log.debug(f"Reset account access key. account_name:{account_name}")
        params = {
            'AccountName': account_name
        }

        (code, body) = await self._arbitrary_request('ResetAccountAccessKey', params, '/', 'POST')
        Log.debug(f"Reset account access key status code: {code}")
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            result = self._extract_element(
                const.S3_RESET_ACCOUNT_ACCESS_KEY_RESP_ACCOUNT_PATH, body)
            resp = self._create_response(ExtendedIamAccount, result, self.EXT_ACCOUNT_MAPPING)

            # TODO: find out why there is no email the response
            return resp

    @Log.trace_method(Log.DEBUG)
    async def delete_account(self, account_name: str, force: bool = False) -> Union[bool, IamError]:
        """
        Delete IAM account

        Note that in order to delete account_name we need to use access key
        and secret key of account_name

        :param account_name: account's name.
        :force: flag if delete anyways.
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
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def create_user(self, user_name: str) -> Union[IamUser, IamError]:
        """
        Create an IAM user.

        :param: IAM user name.
        :returns: IamUser in case of success, IamError otherwise
        """

        Log.debug(f"Create iam user. user_name:{user_name}")
        params = {
            'UserName': user_name
        }

        (code, body) = await self._arbitrary_request('CreateUser', params, '/', 'POST')
        Log.debug(f"Create iam user status code: {code}")
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            user = self._extract_element(const.S3_CREATE_USER_RESP_USER_PATH, body)
            return self._create_response(IamUser, user, self.IAM_USER_MAPPING)

    @Log.trace_method(Log.DEBUG, exclude_args=['user_password'])
    async def create_user_login_profile(
        self, user_name: str, user_password: str, require_reset: Optional[bool] = False
    ) -> Union[None, IamError]:
        """
        Create IAM user login profile.

        :param user_name: IAM user's name.
        :param user_password: IAM user's password.
        :param require_reset: flag if the user needs to reset the password once logged in.
        :returns: None in case of success, IamError otherwise
        """

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
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            return None

    @Log.trace_method(Log.DEBUG, exclude_args=['user_password'])
    async def update_user_login_profile(
        self, user_name: str, user_password: str, require_reset: Optional[bool] = False
    ) -> Union[bool, IamError]:
        """
        User's login profile update.

        Note that it is required to provide S3 account credentials.

        :param user_name: IAM user's name.
        :param user_password: IAM user's password.
        :param require_reset: flag if the user needs to reset the password once logged in.
        :returns: True in case of success, IamError otherwise.
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
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def list_users(
        self, marker: Optional[str] = None, max_items: Optional[int] = None
    ) -> Union[IamUserListResponse, IamError]:
        """
        List IAM users.

        Note that max_items and marker are not working for now!!

        :param marker: pagination marker from the previous response.
        :param max items: maximum number of items to return.
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
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            users = self._extract_element(
                ('ListUsersResponse', 'ListUsersResult', 'Users'), body, is_list=True)
            converted_users = []
            for raw in users:
                converted_users.append(self._create_response(IamUser, raw, self.IAM_USER_MAPPING))

            resp = IamUserListResponse()
            resp.iam_users = converted_users
            raw = self._extract_element(const.S3_LIST_USERS_RESP_ISTRUNCATED_PATH, body)

            resp.is_truncated = raw == 'true'
            if resp.is_truncated:
                resp.marker = self._extract_element(const.S3_LIST_USERS_RESP_MARKER_PATH, body)

            return resp

    @Log.trace_method(Log.DEBUG)
    async def delete_user(self, user_name: str) -> Union[bool, IamError]:
        """
        Deletes IAM user.

        :param user_name: IAM user's name.
        :returns: True in case of success, IamError otherwise.
        """

        Log.debug(f"Delete iam User: {user_name}")
        params = {
            'UserName': user_name
        }

        (code, body) = await self._arbitrary_request('DeleteUser', params, '/', 'POST')
        Log.debug(f"Delete iam User status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    @Log.trace_method(Log.DEBUG)
    async def get_user(self, user_name: str) -> Union[IamUser, IamError]:
        """
        Query the IAM user.

        TODO: Currently is not supported by our IAM server.

        :param user_name: IAM user's name.
        :returns: IamUser if user exists, None if not and IamError in case of error.
        """

        raise NotImplementedError()

        params = {
            'UserName': user_name
        }

        (code, body) = await self._arbitrary_request('GetUser', params, '/', 'POST')
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return None

    @Log.trace_method(Log.DEBUG)
    async def update_user(
        self, user_name: str, new_user_name: Optional[str] = None
    ) -> Union[bool, IamError]:
        """
        Update an existing IAM user.

        :param user_name: TODO: find out details about this field.
        :param new_user_name: If not None, user will be renamed accordingly.
        :returns: True in case of success, IamError in case of problem.
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
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            # TODO: our IAM server does not return the updated user information
            return True

    async def create_user_access_key(
        self, user_name: Optional[str] = None
    ) -> Union[ExtendedIamAccount, IamError]:
        """
        Creates an access key id and secret key for IAM user.

        :param user_name: IAM user name, if None, user is deduced from the current session
        :returns: credentials in case of success, IamError in case of problem
        """

        Log.info(f"Create access key for user: {user_name}")
        params = {}
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(
            const.S3_IAM_CMD_CREATE_ACCESS_KEY, params, '/', 'POST')
        Log.info(f"Create access key status code: {code}")
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            creds = self._extract_element(const.S3_CREATE_ACCESS_KEY_RESP_KEY_PATH, body)
            return self._create_response(IamUserCredentials, creds,
                                         self.IAM_USER_CREDENTIALS_MAPPING)

    async def update_user_access_key(
        self, access_key_id: str, status: str, user_name: Optional[str] = None
    ) -> Union[bool, IamError]:
        """
        Updates an access key status (active/inactive) for IAM user.

        :param user_name: IAM user's name, if None, user is deduced from the current session.
        :param access_key_id: access key ID.
        :param status: new active key status (Active/inactive).
        :returns: true in case of success, IamError in case of problem.
        """

        Log.info(f"Update access key {access_key_id} for user: {user_name}"
                 f" with status {status}")
        params = {
            'AccessKeyId': access_key_id,
            'Status': status
        }
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(
            const.S3_IAM_CMD_UPDATE_ACCESS_KEY, params, '/', 'POST')
        Log.info(f"Update access key status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    async def get_user_access_key_last_used(
        self, access_key_id: str, user_name: Optional[str] = None
    ) -> Union[IamAccessKeyLastUsed, IamError]:
        """
        Retrieve the timestamp of the last access key usage.

        :param access_key_id: access key ID.
        :param user_name: IAM user name, if None, user is deduced from the current session.
        :returns: timestamp in case of success, IamError in case of problem.
        """

        Log.info(f"Get last used time of IAM user's {user_name} access key {access_key_id}")
        params = {
            'AccessKeyId': access_key_id
        }
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(
            const.S3_IAM_CMD_GET_ACCESS_KEY_LAST_USED, params, '/', 'POST')
        Log.info(f"Update access key status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            info = self._extract_element(const.S3_GET_ACCESS_KEY_LAST_RESP_KEY_PATH, body)
            return self._create_response(IamAccessKeyLastUsed, info,
                                         self.IAM_ACCESS_KEY_LAST_USED_MAPPING)

    async def list_user_access_keys(
        self, user_name: Optional[str] = None, marker: Optional[str] = None,
        max_items: Optional[int] = None
    ) -> Union[IamAccessKeysListResponse, IamError]:
        """
        Get the list of access keys for IAM user.

        Note that max_items and marker are not working for now!

        :param user_name: IAM user name, if None, user is deduced from the current session.
        :param marker: pagination marker from the previous response.
        :param max_items: maximum number of access keys to return in single response.
        :returns: IamAccessKeysListResponse in case of success, IamError otherwise.
        """

        Log.info(f"List IAM user's {user_name} access keys. marker: {marker},"
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
        Log.info(f"List IAM user's access keys status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            keys = self._extract_element(
                const.S3_LIST_ACCESS_KEYS_RESP_KEYS_PATH, body, is_list=True)
            converted_keys = []
            for raw in keys:
                converted_keys.append(self._create_response(IamAccessKeyMetadata, raw,
                                      self.IAM_ACCESS_KEY_METADATA_MAPPING))

            resp = IamAccessKeysListResponse()
            resp.access_keys = converted_keys
            raw = self._extract_element(const.S3_LIST_ACCESS_KEYS_RESP_ISTRUNCATED_PATH, body)

            resp.is_truncated = raw == 'true'
            if resp.is_truncated:
                resp.marker = self._extract_element(
                    const.S3_LIST_ACCESS_KEYS_RESP_MARKER_PATH, body)

            return resp

    async def delete_user_access_key(
        self, access_key_id: str, user_name: Optional[str] = None
    ) -> Union[bool, IamError]:
        """
        Delete an access key for IAM user.

        :param user_name: IAM user name, if None, user is deduced from the current session.
        :param access_key_id: ID of the access key to be deleted.
        :returns: true in case of success, IamError in case of problem.
        """

        Log.info(f"Delete access key {access_key_id} for IAM user {user_name}")
        params = {
            'AccessKeyId': access_key_id
        }
        if user_name is not None:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(
            const.S3_IAM_CMD_DELETE_ACCESS_KEY, params, '/', 'POST')
        Log.debug(f"Delete iam User status code: {code}")
        if code != HTTPStatus.OK:
            return self._create_error(code, body)
        else:
            return True

    async def get_tmp_creds(
        self, account_name: str, password: str, duration: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> Union[IamTempCredentials, IamError]:
        """
        Obtain temporary credentials via Login Profile.

        :param account_name: S3 account name.
        :param password: S3 account login profile's password.
        :param duration: Session expiry time (in seconds). If set, it must be greater than 900.
        :param user_name: IAM user's name.
        :returns: IamTempCredentials or IamError instance.
        """

        params = {
            'AccountName': account_name,
            'Password': password
        }

        if duration:
            params['Duration'] = duration
        if user_name:
            params['UserName'] = user_name

        (code, body) = await self._arbitrary_request(
            'GetTempAuthCredentials', params, '/', 'POST')
        if code != HTTPStatus.CREATED:
            return self._create_error(code, body)
        else:
            creds = self._extract_element(const.S3_GET_TMP_CREDS_RESP_CREDS_PATH, body)
            return self._create_response(IamTempCredentials, creds, self.IAM_GET_TMP_CREDS_MAPPING)


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
        bucket = await self._loop.run_in_executor(
            self._executor, self._resource.Bucket, bucket_name)
        # Assume that the bucket is empty, if not, the error will be returned.
        # It is user's responsibility to empty the bucket before the deletion.
        await self._loop.run_in_executor(self._executor, bucket.delete)

    @Log.trace_method(Log.DEBUG)
    async def get_all_buckets(self):
        Log.debug("Get all buckets")
        return await self._loop.run_in_executor(self._executor, self._resource.buckets.all)

    @Log.trace_method(Log.DEBUG)
    async def get_bucket_tagging(self, bucket_name: str):
        # When the tag_set is not available ClientError is raised
        # Need to avoid that in order to iterate over tags for all available buckets
        Log.debug(f"Get bucket tagging: {bucket_name}")

        def _run():
            try:
                tagging = self._resource.BucketTagging(bucket_name)
                tag_set = {tag['Key']: tag['Value'] for tag in tagging.tag_set}
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

    def __init__(self) -> None:
        """
        Initialize S3 plugin
        """

        Log.info('S3 plugin is loaded')

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key', 'secret_key', 'session_token'])
    def get_iam_client(
        self, access_key_id: str, secret_access_key: str,
        connection_config: Optional[S3ConnectionConfig] = None, session_token: Optional[str] = None
    ) -> IamClient:
        """
        Return a management object for S3/IAM accounts.

        :param access_key_id: access key ID.
        :param secret_access_key: secret access key.
        :param connection_config: object with client's configuration.
        :param session_token: session token.
        :returns: IamClient instance.
        """

        if not connection_config:
            raise CsmInternalError('Connection configuration must be provided')

        return IamClient(access_key_id, secret_access_key, connection_config,
                         asyncio.get_event_loop(), session_token)

    @Log.trace_method(Log.DEBUG, exclude_args=['access_key', 'secret_key', 'session_token'])
    def get_s3_client(
        self, access_key_id: str, secret_access_key: str,
        connection_config: Optional[S3ConnectionConfig] = None, session_token: Optional[str] = None
    ) -> S3Client:
        """
        Return a management object for S3/IAM accounts.

        :param access_key_id: access key ID.
        :param secret_access_key: secret access key.
        :param connection_config: object with client's configuration.
        :param session_token: session token.
        :returns: S3Client instance.
        """

        if not connection_config:
            raise CsmInternalError('Connection configuration must be provided')

        return S3Client(access_key_id, secret_access_key, connection_config,
                        asyncio.get_event_loop(), session_token)

    @Log.trace_method(Log.DEBUG, exclude_args=['password'])
    async def get_temp_credentials(
        self, account_name: str, password: str, duration: Optional[int] = None,
        user_name: Optional[str] = None, connection_config: Optional[S3ConnectionConfig] = None
    ) -> Union[IamTempCredentials, IamError]:
        """
        Authentication via some Login Profile.

        :param account_name:
        :param password:
        :param duration: Session expiry time (in seconds). If set, it must be
                         greater than 900.
        :param user_name: TODO: find out details about this field
        :param connection_config: TODO: find out details about this field
        :returns: IamTempCredentials object in case of success, IamError otherwise.
        """

        Log.debug(f"Get temp credentials: {account_name}, user_name:{user_name}")
        iamcli = IamClient('', '', connection_config, asyncio.get_event_loop())
        return await iamcli.get_tmp_creds(account_name, password, duration, user_name)

    @Log.trace_method(Log.DEBUG)
    async def get_s3_audit_logs_schema(
        self, connection_config: Optional[S3ConnectionConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Get S3 audit log schema from the S3 server.

        :returns: JSON with audit log schema.
        """

        Log.debug('Get S3 audit log schema')
        s3cli = S3Client('', '', connection_config)
        headers = {'x-seagate-mgmt-api': "true"}
        payload = {}
        status, raw_schema = await s3cli.http_request(
            headers, payload, '/s3/audit-log/schema', 'GET')
        if status != HTTPStatus.OK:
            raise CsmResourceNotAvailable(f'Failed to retrieve S3 audit log schema: {status}')
        try:
            schema = json.loads(raw_schema)
        except json.JSONDecodeError as jde:
            raise CsmResourceNotAvailable(f'Failed to parse S3 audit log schema: {jde}') from None
        return schema
