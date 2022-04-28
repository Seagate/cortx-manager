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

from .view import CsmView, CsmAuth
from cortx.utils.log import Log
from csm.common.errors import CsmNotFoundError
from csm.common.permission_names import Resource, Action
from csm.core.services.permissions import PermissionSet


USERS_MSG_USER_NOT_FOUND = "users_not_found"


class BasePermissionsView(CsmView):
    """Base class for permissions handling."""

    def __init__(self, request):
        super(BasePermissionsView, self).__init__(request)

    def transform_permissions(self, permissions: PermissionSet) -> dict:
        """
        Transform internal representation of the permission set to the format expected by the UI.

        E.g.
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
@CsmView._app_routes.view("/api/v2/permissions")
class CurrentPermissionsView(BasePermissionsView):
    def __init__(self, request):
        super(CurrentPermissionsView, self).__init__(request)

    """
    GET REST implementation for security permissions request
    """
    @CsmAuth.permissions({Resource.PERMISSIONS: {Action.LIST}})
    async def get(self):
        """Get security permissions."""
        permissions = self.transform_permissions(self.request.session.permissions)
        return permissions


@CsmView._app_routes.view("/api/v1/permissions/{user_id}")
@CsmView._app_routes.view("/api/v2/permissions/{user_id}")
class UserPermissionsView(BasePermissionsView):
    def __init__(self, request):
        super(UserPermissionsView, self).__init__(request)
        self._service = self.request.app["csm_user_service"]
        self._service_dispatch = {}
        self._roles_service = self.request.app["roles_service"]

    @CsmAuth.permissions({Resource.PERMISSIONS: {Action.LIST}})
    async def get(self):
        """Get csm user permissions."""
        Log.debug("Handling csm users permissions get request")
        user_id = self.request.match_info["user_id"]
        try:
            localuser = await self._service.get_user(user_id)
            roles = localuser['roles']
        except CsmNotFoundError:
            raise CsmNotFoundError("There is no such user", USERS_MSG_USER_NOT_FOUND, user_id)
        permissions_internal = await self._roles_service.get_permissions(roles)
        permissions = self.transform_permissions(permissions_internal)
        return permissions
