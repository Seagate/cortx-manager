#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          roles.py
 Description:       Implementation of role management

 Creation Date:     01/16/2020
 Author:            Oleg Babin
                    Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from typing import Iterable, Text
from eos.utils.log import Log
from csm.common.validate import Validator
from csm.common.services import ApplicationService
from csm.core.services.permissions import PermissionSet


class Role:
    """
    User role implementation class.
    The role conceptually is a set of permissions.
    """

    def __init__(self, name: str, permissions: PermissionSet):
        self._name = name
        self._permissions = permissions

    @property
    def name(self) -> str:
        return self._name

    @property
    def permissions(self) -> PermissionSet:
        return self._permissions


class RoleManager:
    """
    This class manages user roles.
    TODO: Use a data base for storing roles persistently.
    """

    NO_ROLE = Role(None, PermissionSet())

    @classmethod
    def _validate_name(cls, name):
        Validator.validate_type(name, str, 'role name')
        # TODO: Validate character set in the string

    @classmethod
    def _validate_permissions(cls, permissions):
        Validator.validate_type(permissions, dict, 'permission set')
        for resource, actions in permissions.items():
            Validator.validate_type(resource, str, 'resource name')
            Validator.validate_type(actions, list, 'actions')
            for action in actions:
                Validator.validate_type(action, str, 'action list element')

    @classmethod
    def _validate_role(cls, name, permissions):
        cls._validate_name(name)
        cls._validate_permissions(permissions)

    @classmethod
    def _validate_roles(cls, roles):
        Validator.validate_type(roles, dict, 'roles argument')
        for name, value in roles.items():
            Validator.validate_type(value, dict, 'role value')
            permissions = value.get('permissions', None)
            if permissions is None:
                raise ValueError(f'Permission set should be specified for a role')
            cls._validate_role(name, permissions)

    def __init__(self, predefined_roles):
        """
        Initialize role manager with the predefined set of roles
        loaded from the json file and passed here.
        This is a temporary solution, later we will store predefined
        roles in the RoleDB during the onboarding.
        """

        Log.info(f'Initializing role manager with predefined roles')
        self._validate_roles(predefined_roles)

        self._roles = {
            name: Role(name, PermissionSet(value['permissions']))
                for name, value in predefined_roles.items()
        }

    async def calc_effective_permissions(self, *role_names):
        """
        Calculate effective set of permissions from a given set of user roles.
        """

        permissions = PermissionSet()
        for role_name in role_names:
            role = self._roles.get(role_name, self.NO_ROLE)
            if role.name is None:
                Log.warn(f"Invalid role name '{role_name}'")
            permissions |= role.permissions
        return permissions

    async def add_role(self, name, permissions):
        """
        Add new user role
        """

        self._validate_role(name, permissions)
        if name in self._roles:
            Log.error(f'Role "{name}" is already present')
            return False
        self._roles[name] = Role(name, PermissionSet(permissions))
        Log.info(f'New role "{name}" has been successfully added')
        return True

    async def delete_role(self, name):
        """
        Delete existing user role
        """

        self._validate_name(name)
        if self._roles.pop(name, None) is not None:
            Log.info(f'Existing role "{name}" has been successfully deleted')
        else:
            Log.warn(f'Role "{name}" does not exist')


class RoleManagementService(ApplicationService):
    """
    Role management application service used by controllers
    """

    def __init__(self, role_manager: RoleManager):
        self._role_manager = role_manager

    async def get_permissions(self, role_names: Iterable[Text]) -> PermissionSet:
        return await self._role_manager.calc_effective_permissions(*role_names)
