#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          storage_caparole_management.py
 Description:       Service(s) for getting roles permissions details

 Creation Date:     1/10/2020
 Author:            Naval Patel


 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import copy
from csm.common.log import Log
from csm.common.services import ApplicationService


class RolesManagementService(ApplicationService):
    """
    Service for Get Roles permissions details
    """
    def __init__(self, roles_dict):
        self.roles_dict = roles_dict

    def get_permissions(self, roles: list):
        """
        Need to skip 'root' role and currently only one role is handled
        In future merging of role to get effective role can come here
        """
        mod_roles = copy.deepcopy(roles)
        if 'root' in mod_roles:
            mod_roles.remove('root')
        return self.roles_dict[mod_roles[0]]
