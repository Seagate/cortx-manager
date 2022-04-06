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

from typing import List
from enum import Enum
from datetime import datetime


class S3ConnectionConfig:
    """
    Configuration options for IAM server access
    """
    host: str
    port: int
    use_ssl: bool = False
    verify_ssl_cert: bool = False
    ca_cert_file: str = None
    debug: bool = False
    max_retries_num: int = None


class IamAccount:
    """
    Primitive information about IAM account - as it is returned by listing them
    """
    account_id: str
    account_name: str
    account_email: str
    canonical_id: str


class ExtendedIamAccount(IamAccount):
    """
    Information about IAM account that is only available after its creation
    """
    access_key_id: str
    secret_key_id: str
    status: str


class IamLoginProfile:
    """
    Information about login profile
    """
    account_name: str
    password_reset_required: bool
    create_date: str  # or datetime?


class IamUser:
    """
    Information about IAM user
    """
    path: str
    user_id: str
    user_name: str
    arn: str


class IamUserListResponse:
    iam_users: List[IamUser]
    marker: str
    is_truncated: bool


class IamAccountListResponse:
    iam_accounts: List[IamAccount]
    marker: str
    is_truncated: bool


class IamUserCredentials:
    user_name: str
    access_key_id: str
    secret_key: str
    status: str


class IamAccessKeyMetadata:
    user_name: str
    access_key_id: str
    status: str


class IamAccessKeyLastUsed:
    last_used: datetime
    region: str
    service_name: str


class IamAccessKeysListResponse:
    access_keys: List[IamAccessKeyMetadata]
    marker: str
    is_truncated: bool


class IamTempCredentials:
    """
    Information about temorary auth credentials for some login profile
    """
    user_name: str  # TODO: server output is very strange for this field
    access_key: str
    secret_key: str
    status: str
    expiry_time: str  # TODO: or datetime?
    session_token: str


class IamErrors(Enum):
    """ Enum with error responses """
    EntityAlreadyExists = 'EntityAlreadyExists'
    AccessKeyAlreadyExists = 'AccessKeyAlreadyExists'
    OperationNotSupported = 'OperationNotSupported'
    InvalidAccessKeyId = 'InvalidAccessKeyId'
    InvalidParameterValue = 'InvalidParameterValue'
    NoSuchEntity = 'NoSuchEntity'
    ExpiredCredential = 'ExpiredCredential'
    InvalidLdapUserId = 'InvalidLdapUserId'
    PasswordPolicyVoilation = 'PasswordPolicyVoilation'
    AccountNotEmpty = 'AccountNotEmpty'
    ExtendedIamAccount = 'ExtendedIamAccount'
    EmailAlreadyExists = 'EmailAlreadyExists'
    DeleteConflict = 'DeleteConflict'
    InvalidCredentials = 'InvalidCredentials'
    BadRequest = 'BadRequest'
    AccessKeyQotaExceeded = 'AccessKeyQuotaExceeded'
    MaxAccountLimitExceeded = 'MaxAccountLimitExceeded'
    MaxUserLimitExceeded = 'MaxUserLimitExceeded'


class IamError:
    """
    Class that describes a non-successful result
    """
    http_status: int
    error_code: IamErrors
    error_message: str
