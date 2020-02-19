#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          permissions.py
 Description:       Implementation of security permissions view

 Creation Date:     1/6/2020
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from .view import CsmView
from csm.common.log import Log
from csm.core.services.permissions import PermissionSet
from csm.common.errors import CsmNotFoundError

USERS_MSG_USER_NOT_FOUND = "users_not_found"


class BasePermissionsView(CsmView):
    """
    Base class for permissions handling
    """

    def __init__(self, request):
        super(BasePermissionsView, self).__init__(request)

    def transform_permissions(self, permissions: PermissionSet) -> dict:
        """
        transform permissions dict resources 
        'alert': ['list, 'update']
        to 
        'alert': {'list': True, 'update': True}
        """
        mod_permissions = {}
        for resource, action_list in permissions._items.items():
            action_dict = {}
            for action in action_list:
                action_dict[action] = True
            mod_permissions[resource] = action_dict
        final_permissions = {}
        final_permissions['permissions'] = mod_permissions
        return final_permissions


@CsmView._app_routes.view("/api/v1/permissions")
class CurrentPermissionsView(BasePermissionsView):
    def __init__(self, request):
        super(CurrentPermissionsView, self).__init__(request)

    """
    GET REST implementation for security permissions request
    """
    async def get(self):
        """
        Calling Security get permissions Get Method
        """
        permissions = self.transform_permissions(self.request.session.permissions) 
        return permissions

@CsmView._app_routes.view("/api/v1/permissions/{user_id}")
class UserPermissionsView(BasePermissionsView):
    def __init__(self, request):
        super(UserPermissionsView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}
        self._roles_service = self.request.app["roles_service"]

    async def get(self):
        """
        Calling Security get csm user permissions Get Method
        """
        Log.debug("Handling csm users permissions get request")
        user_id = self.request.match_info["user_id"]
        try:
            localuser = await self._service.get_user(user_id)
            roles = localuser['roles']
        except CsmNotFoundError:
            raise CsmNotFoundError("There is no such user", USERS_MSG_USER_NOT_FOUND, user_id)
        permissions_internal = self._roles_service.get_permissions(roles)
        permissions = self.transform_permissions(permissions_internal)
        return permissions
