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

from csm.common.services import ApplicationService
from csm.eos.plugins.s3 import S3Client, IamConnectionConfig
from csm.common.conf import Conf
from csm.common.log import Log
from csm.core.blogic import const
from csm.core.providers.providers import Response
import asyncio
from typing import Union, Dict
from csm.core.blogic.models.s3 import IamError, IamErrors
from csm.common.errors import CsmInternalError

class IamUsersService(ApplicationService):
    """
    Service for IAM user management
    """

    def __init__(self, s3_session):
        self._s3_client = self.create_s3_connection_obj(s3_session)

    @Log.trace_method(Log.DEBUG)
    async def create_s3_connection_obj(self, s3_session: Dict) -> S3Client:
        """
        This Method will create S3 object for connection fetching request headers
        :param s3_session:  S3 Account Logged in info. :type: Dict
        :return:
        """
        # Create Connection Object for S3
        iam_connection_config = IamConnectionConfig()
        iam_connection_config.host = Conf.get(const.CSM_GLOBAL_INDEX, "S3.host")
        iam_connection_config.port = Conf.get(const.CSM_GLOBAL_INDEX, "S3.port")
        iam_connection_config.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX,
                                                              "S3.max_retries_num")

        #Create S3 Client Connection Object
        s3_client_object = S3Client(s3_session["access_key_id"],
                                    s3_session["secret_key_id"],
                                    iam_connection_config,
                                    asyncio.get_event_loop(),
                                    s3_session["session_token"])

        return s3_client_object

    @Log.trace_method(Log.DEBUG)
    async def create_user(self, user_name: str, password: str, path: str = "/",
                          require_reset=False) -> [Response, Dict]:
        """
        This Method will create an IAM User in S3 user Account.
        :param user_name: User name for New user. :type: str
        :param password: Password for new IAM user :type: str
        :param path: path for he user if defined else "/" :type: str
        :param require_reset: Required to reset Password :type: bool
        :return: {"msg": "User Created Successfully."}
        """

        # Create Iam User in System.
        user_creation_resp = await self._s3_client.create_user(user_name, path)
        if hasattr(user_creation_resp, "error_code"):
            return await  self._handle_error(user_creation_resp)
        # Create Iam User's Login Profile.
        user_login_profile_resp = await self._s3_client.create_user_login_profile(
            user_name, password, require_reset)
        if user_login_profile_resp and hasattr(user_login_profile_resp, "error_code"):
            #If User creation Failed delete the user.
            await self._s3_client.delete_user(user_name)
            return await  self._handle_error(user_login_profile_resp)
        return vars(user_creation_resp)

    @Log.trace_method(Log.DEBUG)
    async def list_users(self, path_prefix="/") -> Union[Response, Dict]:
        """
        This Method Fetches Iam User's
        :param path_prefix: Path For user's Search "/account/sub_account/" :type:str
        :return:
        """

        #Fetch IAM Users
        users_list_response = await self._s3_client.list_users(path_prefix)
        if hasattr(users_list_response, "error_code"):
            return await  self._handle_error(users_list_response)
        iam_users_list = vars(users_list_response)
        iam_users_list["iam_users"] = [vars(each_user) for each_user in iam_users_list["iam_users"]]
        return iam_users_list

    @Log.trace_method(Log.DEBUG)
    async def delete_user(self, user_name: str) -> Dict:
        """
        This method deletes the s3 Iam user.
        :param user_name: S3 User Name :type: str
        :return:
        """
        #Delete Given Iam User
        user_delete_response = await  self._s3_client.delete_user(user_name)
        if hasattr(user_delete_response, "error_code"):
            return await self._handle_error(user_delete_response)
        return {"message": "User Deleted Successfully."}

    def update_user(self, user_name: str):
        pass

    @Log.trace_method(Log.DEBUG)
    async def _handle_error(self, iam_error_obj:  IamError):
        status_code_mapping = {
            IamErrors.EntityAlreadyExists.value : 409,
            IamErrors.OperationNotSupported.value : 404,
            IamErrors.InvalidAccessKeyId.value : 422,
            IamErrors.InvalidParameterValue.value : 400,
            IamErrors.NoSuchEntity.value : 404
        }
        if iam_error_obj.error_code not in status_code_mapping.keys():
            return CsmInternalError(iam_error_obj)
        return Response(rc=status_code_mapping.get(iam_error_obj.error_code),
                    output=iam_error_obj.error_message)