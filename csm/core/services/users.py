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

# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from cortx.utils.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from csm.core.data.models.users import User, UserType, Passwd
from csm.common.errors import (CsmNotFoundError, CsmError, InvalidRequest,
                                CsmPermissionDenied, ResourceExist)
import time
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from cortx.utils.data.access.filters import Compare, And, Or
from cortx.utils.data.access import Query, SortOrder
from csm.core.blogic import const
from schematics import Model
from schematics.types import StringType, BooleanType, IntType
from typing import Optional, Iterable
from cortx.utils.conf_store.conf_store import Conf

class UserManager:
    """
    The class encapsulates user management activities.
    This is intended to be used during user management and authorization
    """
    def __init__(self, storage: DataBaseProvider) -> None:
        self.storage = storage

    async def create(self, user: User) -> User:
        """
        Stores a new user
        :param user: User model instance
        """
        # validate the model
        existing_user = await self.get(user.user_id)
        if existing_user:
            raise ResourceExist(f"User already exists: {existing_user.user_id}", USERS_MSG_ALREADY_EXISTS)

        return await self.storage(User).store(user)

    async def get(self, user_id) -> User:
        """
        Fetches a single user.
        :param user_id: User identifier
        :returns: User object in case of success. None otherwise.
        """
        Log.debug(f"Get user service user id:{user_id}")
        # TODO In absence of ComapareIgnoreCase manually filtering 
        # query = Query().filter_by(Compare(User.to_native("user_id").lower(), '=', user_id.lower()))
        # return next(iter(await self.storage(User).get(query)), None)
        all_users = await self.get_list()
        for user in all_users:
            if user["user_id"].lower() == user_id.lower():
                return user
        return None

    async def delete(self, user_id: str) -> None:
        Log.debug(f"Delete user service user id:{user_id}")
        await self.storage(User).delete(Compare(User.user_id, '=', user_id))

    async def get_list(self, offset: int = None, limit: int = None,
                       sort: SortBy = None) -> List[User]:
        """
        Fetches the list of users.
        :param offset: Number of items to skip.
        :param limit: Maximum number of items to return.
        :param sort: What field to sort on.
        :returns: A list of User models
        """
        query = Query()

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        if sort:
            query = query.order_by(getattr(User, sort.field), sort.order)
        Log.debug(f"Get user list service query: {query}")
        return await self.storage(User).get(query)

    async def get_list_alert_notification_emails(self) -> List[User]:
        """ return list of emails for user having alert_notification true"""
        query = Query().filter_by(Compare(User.alert_notification, '=', True))
        user_list = await self.storage(User).get(query)
        return [user.email for user in user_list]

    async def count(self):
        return await self.storage(User).count(None)

    async def save(self, user: User):
        """
        Stores an already existing user.
        :param user:
        """
        # TODO: validate the model
        await self.storage(User).store(user)


USERS_MSG_USER_NOT_FOUND = "users_not_found"
USERS_MSG_PERMISSION_DENIED = "user_permission_denied"
USERS_MSG_ALREADY_EXISTS = "users_already_exists"
USERS_MSG_CANNOT_SORT = "users_non_sortable_field"
USERS_MSG_UPDATE_NOT_ALLOWED = "update_not_allowed"


class CsmUserService(ApplicationService):
    """
    Service that exposes csm user management actions from the csm core.
    """
    def __init__(self, provisioner, user_mgr: UserManager):
        self.user_mgr = user_mgr
        self._provisioner = provisioner

    def _user_to_dict(self, user: User):
        """ Helper method to convert user model into a dictionary repreentation """
        return {
            "id": user.user_id,
            "username": user.user_id,
            "user_type": user.user_type,
            "roles": user.roles,
            "email": user.email,
            "created_time": user.created_time.isoformat() + 'Z',
            "updated_time": user.updated_time.isoformat() + 'Z'
        }

    async def create_user(self, user_id: str, password: str, **kwargs) -> dict:
        """
        Handles the csm user creation
        :param user_id: User identifier
        :param user_password: User password (not hashed)
        :param roles: List of roles of the user
        :param interfaces: List of user interfaces
        :returns: A dictionary describing the newly created user.
        In case of error, an exception is raised.
        """
        Log.debug(f"Create user service. user_id: {user_id}")
        user = User.instantiate_csm_user(user_id, password)
        user.update(kwargs)
        user['alert_notification'] = True
        await self.user_mgr.create(user)
        return self._user_to_dict(user)

    async def create_super_user(self, user_id: str, password: str,
                                email: str) -> dict:
        """
        Handles the preboarding super user creation
        :param user_id: User identifier
        :param password: User password (not hashed)
        :param email: User email
        :returns: A dictionary describing the newly created user.
        In case of error, an exception is raised.
        """
        Log.debug(f"Create root user service user_id: {user_id}")
        if await self.user_mgr.count() != 0:
            # The root user is allowed to be created only once during preboarding.
            # Non-zero user count means that such user was already created.
            return None

        # TODO: Decide the default preboarding user roles once we
        # implement user role management. Replace this hardcoded values
        # with proper constants.
        roles = [const.CSM_SUPER_USER_ROLE, const.CSM_MANAGE_ROLE]
        user = User.instantiate_csm_user(user_id, password, email=email, roles=roles,
                                         alert_notification=True)
        await self.user_mgr.create(user)
        return self._user_to_dict(user)

    async def get_user(self, user_id: str):
        """
        Fetches a single user.
        """
        Log.debug(f"Get user service user id: {user_id}")
        user = await self.user_mgr.get(user_id)
        if not user:
            raise CsmNotFoundError(f"User does not exist: {user_id}", USERS_MSG_USER_NOT_FOUND)
        return self._user_to_dict(user)

    async def get_user_list(self, limit, offset, sort_by, sort_dir):
        """
        Fetches the list of existing users.
        """
        user_list = await self.user_mgr.get_list(offset or None, limit or None,
            SortBy(sort_by, SortOrder.ASC if sort_dir == "asc" else SortOrder.DESC))

        field_mapping = {
            "id": "user_id",
            "username": "user_id"
        }
        if sort_by in field_mapping:
            sort_by = field_mapping[sort_by]

        if sort_by and sort_by not in const.CSM_USER_SORTABLE_FIELDS:
            raise InvalidRequest("Cannot sort by the selected field", USERS_MSG_CANNOT_SORT)

        return [self._user_to_dict(x) for x in user_list]

    async def get_user_count(self):
        """
        Return the count of existing users
        """
        return await self.user_mgr.count()

    async def delete_user(self, user_id: str, loggedin_user_id: str):
        """ User deletion """
        Log.debug(f"Delete user service user_id: {user_id}.")
        user = await self.user_mgr.get(user_id)
        if not user:
            raise CsmNotFoundError(f"User does not exist: {user_id}", USERS_MSG_USER_NOT_FOUND)
        if self.is_super_user(user):
            raise CsmPermissionDenied("Cannot delete admin user",
                                      USERS_MSG_PERMISSION_DENIED, user_id)
        loggedin_user = await self.user_mgr.get(loggedin_user_id)
        # Is Logged in user normal user
        if not self.is_super_user(loggedin_user):
            if user_id.lower() != loggedin_user_id.lower():
                raise CsmPermissionDenied("Normal user cannot delete other user",
                                          USERS_MSG_PERMISSION_DENIED, user_id)

        await self.user_mgr.delete(user.user_id)
        return {"message": "User Deleted Successfully."}

    async def _validation_for_update_by_superuser(self, user_id: str, user: User, new_values: dict):
        """
        Validation done for updation by super user.
        """
        current_password = new_values.get(const.CSM_USER_CURRENT_PASSWORD, None)
        if self.is_super_user(user) and not current_password:
            raise InvalidRequest("Value for current_password is required",
                                    USERS_MSG_UPDATE_NOT_ALLOWED, user_id)

        if self.is_super_user(user) and ('roles' in new_values):
            raise CsmPermissionDenied("Cannot change roles for admin user",
                                    USERS_MSG_PERMISSION_DENIED, user_id)

    async def _validation_for_update_by_normal_user(self, user_id: str, loggedin_user_id: str,
                                                    new_values: dict):
        """
        Validation done for updation by normal  user.
        """
        current_password = new_values.get(const.CSM_USER_CURRENT_PASSWORD, None)
        if user_id.lower() != loggedin_user_id.lower():
            raise CsmPermissionDenied("Non admin user cannot change other user",
                                    USERS_MSG_PERMISSION_DENIED, user_id)
        
        if not current_password:
            raise InvalidRequest("Value for current_password is required",
                                    USERS_MSG_UPDATE_NOT_ALLOWED, user_id)

        if 'roles' in new_values:
            raise CsmPermissionDenied("Non admin user cannot change roles for self",
                                      USERS_MSG_PERMISSION_DENIED, user_id)
       
    async def update_user(self, user_id: str, new_values: dict, loggedin_user_id: str) -> dict:
        """
        Update user .
        """
        Log.debug(f"Update user service user_id: {user_id}.")
        user = await self.user_mgr.get(user_id)
        if not user:
            raise CsmNotFoundError(f"User does not exist: {user_id}", USERS_MSG_USER_NOT_FOUND)

        current_password = new_values.get(const.CSM_USER_CURRENT_PASSWORD, None)
        loggedin_user = await self.user_mgr.get(loggedin_user_id)
        # Is Logged in user super user
        if self.is_super_user(loggedin_user):
            await self._validation_for_update_by_superuser(user_id, user, new_values)
        else:
            await self._validation_for_update_by_normal_user(user_id, loggedin_user_id, new_values)
        
        if current_password and not self._verfiy_current_password(user, current_password):
            raise InvalidRequest("Cannot update user details without valid current password",
                                      USERS_MSG_UPDATE_NOT_ALLOWED)
        
        user.update(new_values)
        await self.user_mgr.save(user)
        return self._user_to_dict(user)

    def _verfiy_current_password(self, user: User, password):
        """
        Verify current password of user .
        """
        return Passwd.verify(password, user.password_hash)

    def is_super_user(self, user: User):
        """ Check if user is super user """
        return const.CSM_SUPER_USER_ROLE in user.roles
