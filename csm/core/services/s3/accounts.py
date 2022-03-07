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

import time

from typing import Dict

from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log
from csm.common.errors import CsmInternalError, CsmNotFoundError
from csm.common.services import ApplicationService
from csm.core.data.models.s3 import S3ConnectionConfig, IamError, IamErrors
from csm.core.services.sessions import S3Credentials, LocalCredentials
from csm.core.services.s3.utils import S3BaseService, CsmS3ConfigurationFactory, IamRootClient


# TODO: the access to this service must be restricted to CSM users only (?)
class S3AccountService(S3BaseService):
    """
    Service for S3 account management
    """
    def __init__(self, s3plugin):
        """
        Initialize S3AccountService.

        :param s3plugin: S3 plugin object.
        """
        self._s3plugin = s3plugin
        #TODO
        """
        Password should be taken as input and not read from conf file directly.
        """
        self._s3_root_client = IamRootClient()

    @Log.trace_method(Log.DEBUG, exclude_args=['password'])
    async def create_account(self, account_name: str, account_email: str, password: str,\
                                access_key: str, secret_key: str) -> Dict:
        """
        S3 account creation
        :param account_name:
        :param account_email:
        :param password:
        :returns: a dictionary describing the newly created S3 account. Exception otherwise.
        """
        Log.debug(f"Creating s3 account. account_name: {account_name}")
        account = await self._s3_root_client.create_account(account_name, account_email,\
                                                                access_key, secret_key)
        if isinstance(account, IamError):
            self._handle_error(account, args={'account_name': account_name})

        # Adding wait for replication in ldap to complete
        time.sleep(3)

        account_client = self._s3plugin.get_iam_client(account.access_key_id,
            account.secret_key_id, CsmS3ConfigurationFactory.get_iam_connection_config())

        try:
            # Note that the order of commands below is important
            # If profile creation fails, we can easily remove the account
            # If a profile is created, we can still remove the account
            Log.debug(f"Creating Login profile for account: {account}")
            profile = await account_client.create_account_login_profile(account.account_name, password)
            if isinstance(profile, IamError):
                self._handle_error(profile, args={'account_name': account_name})
        except Exception as e:
            await account_client.delete_account(account.account_name)
            raise e

        return {
            "account_name": account.account_name,
            "account_email": account.account_email,
            "account_id": account.account_id,
            "canonical_id": account.canonical_id,
            "access_key": account.access_key_id,
            "secret_key": account.secret_key_id
        }

    @Log.trace_method(Log.DEBUG)
    async def get_account(self, account_name) -> dict:
        account = await self._s3_root_client.get_account(account_name)
        if isinstance(account, IamError):
            self._handle_error(account)
        if account is None:
            return None
        return {
            "account_name": account.account_name,
            "account_email": account.account_email
        }

    @Log.trace_method(Log.DEBUG)
    async def list_accounts(self, session, continue_marker=None, page_limit=None,
                            demand_all_accounts=False) -> dict:
        """
        Fetch a list of s3 accounts.
        :param session: session object of S3Credentials or LocalCredentials
        :param continue_marker: Marker that must be used in order to fetch another
                                portion of data
        :param page_limit: If set, this will limit the maximum number of items tha will be
                           returned in one batch
        :demand_all_accounts: When set to True, returns full list of s3 account regardless
                              of session type. Needed for internal calls
        :returns: a dictionary containing account list and, if the list is truncated, a marker
                  that can be used for fetching subsequent batches
        """
        # TODO: right now the remote server does not seem to support pagination
        Log.debug(f"Listing accounts. continue_marker:{continue_marker}, "
                  f"page_limit:{page_limit}")
        accounts = await self._s3_root_client.list_accounts(max_items=page_limit,
            marker=continue_marker)
        if isinstance(accounts, IamError):
            self._handle_error(accounts)
        accounts_list = []
        # CSM user is allowed to list all the S3 users in system.
        if isinstance(session, LocalCredentials) or demand_all_accounts:
            for acc in accounts.iam_accounts:
                accounts_list.append(
                        {
                            "account_name": acc.account_name,
                            "account_email": acc.account_email
                        }
                    )
        # S3 user is not allowed to list all s3 user in system.
        # Allowed to list only himself.
        elif isinstance(session, S3Credentials):
            for acc in accounts.iam_accounts:
                if acc.account_name.lower() == session.user_id.lower():
                    accounts_list.append(
                        {
                            "account_name": acc.account_name,
                            "account_email": acc.account_email
                        }
                    )
                    break
        resp = {
            "s3_accounts": accounts_list,
        }
        if accounts.is_truncated:
            resp["continue"] = accounts.marker
        Log.debug(f"List account response: {resp}")
        return resp

    @Log.trace_method(Log.DEBUG, exclude_args=['password'])
    async def patch_account(self, account_name: str, password: str = None,
                            reset_access_key: bool = False) -> dict:
        """
        Patching fields of an existing account.
        At the moment, it is impossible to change password without resetting access key.
        :param account_name: Name of an account to update
        :param password: If set, the password will be updated.
        :param reset_access_key: If set to True, account access and secret key will
                                 be reset
        :returns: a dictionary describing the updated account.
                  In case of an error, an exception is raised.
        """
        Log.debug(f"Patch accounts. account_name:{account_name}, "
                  f"reset_access_key:{reset_access_key}")
        client = self._s3_root_client
        response = {
            "account_name": account_name
        }

        # # TODO: currently there is no way to fetch email of an already existing account
        if reset_access_key:
            new_creds = await client.reset_account_access_key(account_name)
            if isinstance(new_creds, IamError):
                self._handle_error(new_creds)

            response["access_key"] = new_creds.access_key_id
            response["secret_key"] = new_creds.secret_key_id

            client = self._s3plugin.get_iam_client(new_creds.access_key_id,
                new_creds.secret_key_id, CsmS3ConfigurationFactory.get_iam_connection_config())

        if password:
            Log.debug(f"Update Login Profile for account {account_name}")
            new_profile = await client.update_account_login_profile(account_name,
                    password)

            if isinstance(new_profile, IamError):
                # Update failed
                self._handle_error(new_profile)
        return response

    @Log.trace_method(Log.DEBUG)
    async def delete_account(self, account_name: str):
        """
        S3 account deletion
        :param s3_session: S3 Accounts Session Details
        :param account_name: Account Name to Delete Account.
        :returns: dictionary in case of success. Otherwise throws an exception.
        """
        Log.debug(f"Delete account service. account_name:{account_name}")
        result = await self._s3_root_client.delete_account(account_name)
        if isinstance(result, IamError):
            self._handle_error(result)
        return {"message": "Account Deleted Successfully."}
