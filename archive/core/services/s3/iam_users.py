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

from typing import Union, Dict
from cortx.utils.log import Log
from csm.core.data.models.s3 import IamErrors, IamError
from csm.core.providers.providers import Response
from csm.core.services.s3.utils import S3BaseService, CsmS3ConfigurationFactory
from csm.plugins.cortx.s3 import IamClient


class IamUsersService(S3BaseService):
    """
    Service for IAM user management
    """

    def __init__(self, s3plugin):
        self._s3plugin = s3plugin
        # S3 Connection Object.
        self._iam_connection_config = CsmS3ConfigurationFactory.get_iam_connection_config()

    @Log.trace_method(Log.DEBUG)
    async def fetch_iam_client(self, s3_session: Dict) -> IamClient:
        """
        This Method will create S3 object for connection fetching request headers
        :param s3_session:  S3 Account Logged in info. :type: Dict
        :return:
        """
        # Create S3 Client Connection Object
        s3_client_object = self._s3plugin.get_iam_client(s3_session.access_key,
                                                         s3_session.secret_key,
                                                         self._iam_connection_config,
                                                         s3_session.session_token)

        return s3_client_object

    @Log.trace_method(Log.DEBUG, exclude_args=['password'])
    async def create_user(self, s3_session: Dict, user_name: str, password: str,
                          require_reset=False) -> [Response, Dict]:
        """
        This Method will create an IAM User in S3 user Account.
        :param s3_session: S3 session's details. :type: dict
        :param user_name: User name for New user. :type: str
        :param password: Password for new IAM user :type: str
        :param require_reset: Required to reset Password :type: bool
        """

        # Create Iam User in System.
        s3_client = await self.fetch_iam_client(s3_session)
        Log.debug(f"Create IAM User service: \nusername:{user_name}")
        user_creation_resp = await s3_client.create_user(user_name)
        if isinstance(user_creation_resp, IamError):
            self._handle_error(user_creation_resp)
        # Create Iam User's Login Profile.
        user_login_profile_resp = await s3_client.create_user_login_profile(
            user_name, password, require_reset)
        if isinstance(user_login_profile_resp, IamError):
            # If User creation Failed delete the user.
            await s3_client.delete_user(user_name)
            self._handle_error(user_login_profile_resp)
        # Create IAM user's access key
        user_creds_resp = await s3_client.create_user_access_key(user_name=user_name)
        if isinstance(user_creds_resp, IamError):
            await s3_client.delete_user(user_name)
            self._handle_error(user_creds_resp)
        return {
            **vars(user_creation_resp),
            'access_key_id': user_creds_resp.access_key_id,
            'secret_key': user_creds_resp.secret_key
        }

    @Log.trace_method(Log.DEBUG)
    async def list_users(self, s3_session: Dict) -> Union[Response, Dict]:
        """
        This Method Fetches Iam User's
        :param s3_session: S3 session's details. :type: dict
        :return:
        """
        s3_client = await  self.fetch_iam_client(s3_session)
        # Fetch IAM Users
        Log.debug(f"List IAM User service:")
        users_list_response = await s3_client.list_users()
        if isinstance(users_list_response, IamError):
            self._handle_error(users_list_response)
        iam_users_list = vars(users_list_response)
        iam_users_list["iam_users"] = [vars(each_user)
                                       for each_user in iam_users_list["iam_users"]
                                       if not vars(each_user)["user_name"] == "root" ]
        return iam_users_list

    @Log.trace_method(Log.DEBUG, exclude_args=['user_password'])
    async def patch_user(self, s3_session: Dict, user_name: str, password: str,
                         require_reset: bool = False) -> Dict:
        """
        Patch existing IAM user's loging profile.
        :param user_name: the user name
        :param password: the password to be updated.
        :param require_reset: if set, the password will be reset
        :returns: a dictionary describing the updated account.
                  In case of an error, an exception is raised.
        """
        Log.debug(f"Patch IAM user user_name:{user_name}")
        client = await self.fetch_iam_client(s3_session)
        response = {
            "user_name": user_name
        }
        Log.debug(f"Update Login Profile for user {user_name}")
        new_profile = await client.update_user_login_profile(user_name, password)

        if isinstance(new_profile, IamError):
            # Update failed
            self._handle_error(new_profile)
        return response

    @Log.trace_method(Log.DEBUG)
    async def delete_user(self, s3_session: Dict, user_name: str) -> Dict:
        """
        This method deletes the s3 Iam user.
        :param s3_session: S3 session's details. :type: dict
        :param user_name: S3 User Name :type: str
        :return:
        """
        Log.debug(f"Delete IAM User service: Username:{user_name}")
        s3_client = await  self.fetch_iam_client(s3_session)

        list_access_keys_resp = await s3_client.list_user_access_keys(user_name=user_name)
        if isinstance(list_access_keys_resp, IamError):
                self._handle_error(list_access_keys_resp)

        for access_key in list_access_keys_resp.access_keys:
            del_accesskey_resp = await s3_client.delete_user_access_key(access_key.access_key_id, user_name=user_name)
            if isinstance(del_accesskey_resp, IamError) and not del_accesskey_resp.http_status == 404:
                self._handle_error(del_accesskey_resp)

        user_delete_response = await  s3_client.delete_user(user_name)
        if isinstance(user_delete_response, IamError):
            self._handle_error(user_delete_response)
        return {"message": "User Deleted Successfully."}

    def update_user(self, user_name: str):
        pass