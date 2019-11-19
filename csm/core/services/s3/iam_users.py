#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          iam_users.py
 Description:       Services for IAM user management

 Creation Date:     11/04/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.common.services import Service, ApplicationService
from csm.eos.plugins.s3 import S3Client, S3Plugin, IamConnectionConfig
from csm.common.conf import Conf
from csm.common.log import Log
from csm.core.blogic import const
from csm.core.providers.providers import Response
import asyncio
from typing import Union, List

class IamUsersService(ApplicationService):
    """
    Service for IAM user management
    """

    def __init__(self):
        self.iam_connection_config = IamConnectionConfig()
        self.iam_connection_config.host = Conf.get(const.CSM_GLOBAL_INDEX,
                                                   "S3.host")
        self.iam_connection_config.port = Conf.get(const.CSM_GLOBAL_INDEX,
                                                   "S3.port")
        self.iam_connection_config.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX,
                                                              "S3.max_retries_num")

    @Log.trace_method(Log.DEBUG)
    async def create_s3_connection_obj(self, ):
        """
        This Method will create S3 object for connection fetching request headers
        todo: Will be changing this method once the access_key, secret_key and
            session_token will be fetched from User's session management.
        :return:
        """
        s3_conn_obj = S3Plugin()
        account_name = Conf.get(const.CSM_GLOBAL_INDEX, "S3.account_name")
        account_password = Conf.get(const.CSM_GLOBAL_INDEX, "S3.account_password")
        response = await s3_conn_obj.get_temp_credentials(account_name, account_password,
                                                          connection_config=self.iam_connection_config)
        return response.access_key, response.secret_key, response.session_token

    @Log.trace_method(Log.DEBUG)
    async def create_user(self, user_name: str, password: str, path: str = "/",
                          require_reset=False) -> [Response]:
        """
        This Method will create an IAM User in S3 user Account.
        :param user_name: User name for New user. :type: str
        :param password: Password for new IAM user :type: str
        :param path: path for he user if defined else "/" :type: str
        :return: {"msg": "User Created Successfully."}
        """
        access_key_id, secret_key_id, session_token = await self.create_s3_connection_obj()
        s3_client_object = S3Client(access_key_id, secret_key_id,
                                    self.iam_connection_config,
                                    asyncio.get_event_loop(),
                                    session_token)
        # Create Iam User in System.
        user_creation_resp = await s3_client_object.create_user(user_name, path)
        if hasattr(user_creation_resp, "error_code"):
            return Response(rc=user_creation_resp.error_code,
                            output=user_creation_resp.error_message)
        # Create Iam User's Login Profile.
        user_login_profile_resp = await s3_client_object.create_user_login_profile(
            user_name, password, require_reset)
        if user_login_profile_resp and hasattr(user_login_profile_resp, "error_code"):
            return Response(rc=user_login_profile_resp.error_code,
                            output=user_login_profile_resp.error_message)

        return Response(rc=200, output="User Created Successfully.")

    @Log.trace_method(Log.DEBUG)
    async def list_users(self, path_prefix=None, marker=None, max_items=None) -> Union[Response, List]:
        """
        This Method Fetches Iam User's
        :param path_prefix: Path For user's Search "/account/sub_account/" :type:str
        :param marker: marker for pagination :type:str
        :param max_items: maximum number of Items :type: Int
        :return:
        """
        access_key_id, secret_key_id, session_token = await self.create_s3_connection_obj()
        s3_client_object = S3Client(access_key_id, secret_key_id,
                                    self.iam_connection_config,
                                    asyncio.get_event_loop(),
                                    session_token)
        #Fetch Iam Users
        users_list_response = await s3_client_object.list_users(path_prefix, marker, max_items)
        if hasattr(users_list_response, "error_code"):
            return Response(rc=users_list_response.error_code,
                            output=users_list_response.error_message)
        iam_users_list = vars(users_list_response)
        iam_users_list["iam_users"] = [vars(each_user) for each_user in iam_users_list["iam_users"]]
        return iam_users_list

    @Log.trace_method(Log.DEBUG)
    async def delete_user(self, user_name: str):
        """

        :param user_name:
        :return:
        """
        access_key_id, secret_key_id, session_token = await self.create_s3_connection_obj()
        s3_client_object = S3Client(access_key_id, secret_key_id,
                                    self.iam_connection_config,
                                    asyncio.get_event_loop(),
                                    session_token)
        #Delete Given Iam User
        user_delete_response =  s3_client_object.delete_user(user_name)

        if hasattr(user_delete_response, "error_code"):
            return Response(rc=user_delete_response.error_code,
                            output=user_delete_response.error_message)

        return Response(rc=200,
                        output="User Deleted Successfully.")



    def update_user(self, user_name: str):
        pass
