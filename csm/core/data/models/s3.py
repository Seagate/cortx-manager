"""
 ****************************************************************************
 Filename:          s3.py
 Description:       Contains S3 and IAM related models

 Creation Date:     11/13/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from typing import List
from enum import Enum


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
    OperationNotSupported = 'OperationNotSupported'
    InvalidAccessKeyId = 'InvalidAccessKeyId'
    InvalidParameterValue = 'InvalidParameterValue'
    NoSuchEntity = 'NoSuchEntity'
    ExpiredCredential = 'ExpiredCredential'
    InvalidLdapUserId = 'InvalidLdapUserId'
    PasswordPolicyVoilation = 'PasswordPolicyVoilation'
    AccountNotEmpty = 'AccountNotEmpty'
    ExtendedIamAccount = 'ExtendedIamAccount'


class IamError:
    """
    Class that describes a non-successful result
    """
    error_code: IamErrors
    error_message: str
