#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          s3_accounts.py
 Description:       Services for S3 account management

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
from csm.core.blogic.models.iam import IamUser


class S3AccountService(ApplicationService):
    """
    Service for S3 account management
    """
    def create_account(self, account_name: str, account_email: str, account_password: str):
        pass

    def list_accounts(self):
        pass

    def delete_account(self, account_name: str):
        pass
