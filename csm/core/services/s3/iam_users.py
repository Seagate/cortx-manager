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


class IamUsersService(ApplicationService):
    """
    Service for IAM user management
    """
    def create_user(self, user_name: str, path: str):
        pass

    def list_users(self):
        pass

    def delete_user(self, user_name: str):
        pass

    def update_user(self, user_name: str):
        pass
