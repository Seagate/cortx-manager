#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          roles.py
 Description:       Implementation of role management

 Creation Date:     01/16/2020
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.core.services.permissions import Permissions, R, A

class Role:
    def __init__(self, name, permissions):
        self._name = name
        self._permissions = permissions

    @property
    def name(self):
        return self._name

    @property
    def permissions(self):
        return self._permissions


PREDEFINED_ROLES = [
    Role('root', Permissions({
        R.USER : {A.LIST, A.CREATE, A.DELETE, A.UPDATE},
        })),

    Role('admin', permissions=Permissions({
        R.USER : {A.LIST, A.CREATE, A.DELETE, A.UPDATE},
        R.ALERT: {A.LIST, A.CREATE, A.DELETE, A.UPDATE},
        R.STAT : {A.LIST, A.CREATE, A.DELETE, A.UPDATE},
        R.S3ACCOUNT: {A.LIST, A.CREATE},
        R.S3USER: {},
        })),

    Role('monitor', Permissions({
        R.ALERT: {A.LIST},
        R.USER : {A.LIST},
        R.STAT : {A.LIST},
        })),

    Role('s3account', Permissions({
        R.S3ACCOUNT: {A.UPDATE, A.DELETE},
        R.S3USER: {A.LIST, A.CREATE, A.UPDATE, A.DELETE},
        })),

    Role('s3user', Permissions({
        R.S3USER: {A.UPDATE, A.DELETE},
        })),
]


class RoleManager:

    def __init__(self):
        self._roles = {
            role.name: role
                for role in PREDEFINED_ROLES
        }

    async def calc_effective_permissions(self, *role_names):
        permissions = Permissions()
        for role_name in role_names:
            role = self._roles.get(role_name, None)
            if role is None:
                raise f"Invalid role name '{role_name}'"
            permissions |= role.permissions
        return permissions
