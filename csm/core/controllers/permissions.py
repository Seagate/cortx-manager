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

