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
from enum import Enum, auto
from typing import List, Optional
from cortx.utils.log import Log
from csm.common.services import ApplicationService
from csm.common.queries import SortBy
from csm.core.data.models.users import User, Passwd
from csm.common.errors import (CsmNotFoundError, InvalidRequest, CsmPermissionDenied, ResourceExist)
from cortx.utils.data.db.db_provider import DataBaseProvider
from cortx.utils.data.access.filters import Compare, And
from cortx.utils.data.access import Query, SortOrder
from csm.core.blogic import const


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
            msg = f"User already exists: {existing_user.user_id}"
            raise ResourceExist(msg, USERS_MSG_ALREADY_EXISTS)

        return await self.storage(User).store(user)

    async def get(self, user_id) -> User:
        """
        Fetches a single user.
        :param user_id: User identifier
        :returns: User object in case of success. None otherwise.
        """
        Log.debug(f"Get user service user id:{user_id}")
        # TODO In absence of ComapareIgnoreCase manually filtering
        # query = Query().filter_by(Compare(User.to_native("user_id").lower(),'=',user_id.lower()))
        # return next(iter(await self.storage(User).get(query)), None)
        all_users = await self.get_list()
        for user in all_users:
            if user["user_id"].lower() == user_id.lower():
                return user
        return None

    async def delete(self, user_id: str) -> None:
        Log.debug(f"Delete user service user id:{user_id}")
        await self.storage(User).delete(Compare(User.user_id, '=', user_id))

    async def get_list(self, offset: Optional[int] = None, limit: Optional[int] = None,
                       sort: Optional[SortBy] = None,
                       role: Optional[str] = None, username: Optional[str] = None) -> List[User]:
        """
        Fetches the list of users.
        :param offset: Number of items to skip.
        :param limit: Maximum number of items to return.
        :param sort: What field to sort on.
        :param role: Role to filter the list.
        :returns: A list of User models
        """
        query = Query()
        query_filters = []

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        if sort:
            query = query.order_by(getattr(User, sort.field), sort.order)

        if role:
            query_filters.append(Compare(User.role, '=', role))

        if username:
            query_filters.append(Compare(User.user_id, 'like', username))

        if query_filters:
            query = query.filter_by(And(*query_filters))

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

    async def count_admins(self):
        """
        Counts the number of created CORTX admin users.

        :returns: number of CORTX admin users.
        """
        fltr = Compare(User.role, '=', const.CSM_SUPER_USER_ROLE)
        return await self.storage(User).count(fltr)


USERS_MSG_USER_NOT_FOUND = "users_not_found"
USERS_MSG_PERMISSION_DENIED = "user_permission_denied"
USERS_MSG_ALREADY_EXISTS = "users_already_exists"
USERS_MSG_CANNOT_SORT = "users_non_sortable_field"
USERS_MSG_UPDATE_NOT_ALLOWED = "update_not_allowed"


class UpdateUserRule(Enum):
    """
    The class handles user updating rules across different user roles.
    """
    NONE = auto()
    ALL = auto()
    SELF = auto()
    OTHERS = auto()

    def apply(self, self_update: bool) -> bool:
        """
        Apply the rule.

        Convert the rule to the decision (allowed/not allowed) according to the context.
        :param self_update: flag if the rule is applied to user himself.
        :returns: True if the rule is passed, False otherwise
        """
        decision = True
        if self is UpdateUserRule.NONE:
            decision = False
        elif self is UpdateUserRule.SELF:
            if not self_update:
                decision = False
        elif self is UpdateUserRule.OTHERS:
            if self_update:
                decision = False
        return decision


CSM_USER_PASSWD_UPDATE_RULES = {
    const.CSM_SUPER_USER_ROLE: {
        const.CSM_SUPER_USER_ROLE: UpdateUserRule.ALL,
        const.CSM_MANAGE_ROLE: UpdateUserRule.ALL,
        const.CSM_MONITOR_ROLE: UpdateUserRule.ALL
    },
    const.CSM_MANAGE_ROLE: {
        const.CSM_SUPER_USER_ROLE: UpdateUserRule.NONE,
        const.CSM_MANAGE_ROLE: UpdateUserRule.ALL,
        const.CSM_MONITOR_ROLE: UpdateUserRule.ALL
    },
    const.CSM_MONITOR_ROLE: {
        const.CSM_SUPER_USER_ROLE: UpdateUserRule.NONE,
        const.CSM_MANAGE_ROLE: UpdateUserRule.NONE,
        const.CSM_MONITOR_ROLE: UpdateUserRule.SELF
    }
}

CSM_USER_ROLE_UPDATE_RULES = {
    const.CSM_SUPER_USER_ROLE: {
        const.CSM_SUPER_USER_ROLE: UpdateUserRule.ALL,
        const.CSM_MANAGE_ROLE: UpdateUserRule.ALL,
        const.CSM_MONITOR_ROLE: UpdateUserRule.ALL
    },
    const.CSM_MANAGE_ROLE: {
        const.CSM_SUPER_USER_ROLE: UpdateUserRule.NONE,
        const.CSM_MANAGE_ROLE: UpdateUserRule.OTHERS,
        const.CSM_MONITOR_ROLE: UpdateUserRule.ALL
    },
    const.CSM_MONITOR_ROLE: {
        const.CSM_SUPER_USER_ROLE: UpdateUserRule.NONE,
        const.CSM_MANAGE_ROLE: UpdateUserRule.NONE,
        const.CSM_MONITOR_ROLE: UpdateUserRule.NONE
    }
}


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
            "role": user.role,
            "email": user.email,
            "created_time": user.created_time.isoformat() + 'Z',
            "updated_time": user.updated_time.isoformat() + 'Z',
            "alert_notification": user.alert_notification
        }

    async def create_user(
        self, user_id: str, password: str, role: str, creator_id: Optional[str], **kwargs
    ) -> dict:
        """
        Handles the csm user creation
        :param user_id: User identifier
        :param user_password: User password (not hashed)
        :param creator_id: identifier of the user who triggered the new user creation
        :param role: role of the user
        :param interfaces: List of user interfaces
        :returns: A dictionary describing the newly created user.
        In case of error, an exception is raised.
        """
        Log.debug(f"Create user service. user_id: {user_id}")

        creator = await self.user_mgr.get(creator_id) if creator_id else None
        # Perform pre-creation checks for anonymous user
        if creator is None:
            num_admins = await self.user_mgr.count_admins()
            if role == const.CSM_SUPER_USER_ROLE and num_admins == 0:
                Log.info("Anonymous user is creating the first CORTX admin")
            else:
                raise CsmPermissionDenied("Please, log in to create a user")
        # ... and for logged in user
        else:
            if role == const.CSM_SUPER_USER_ROLE and creator.role != const.CSM_SUPER_USER_ROLE:
                raise CsmPermissionDenied("Only admin user can create other admin users")

        user = User.instantiate_csm_user(user_id, password, role=role, alert_notification=True)
        user.update(kwargs)
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

    async def get_user_list(self, limit, offset, sort_by, sort_dir, role, username):
        """
        Fetches the list of existing users.
        """
        user_list = await self.user_mgr.get_list(
            offset or None,
            limit or None,
            SortBy(sort_by, SortOrder.ASC if sort_dir == "asc" else SortOrder.DESC),
            role, username)

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
        if user.role == const.CSM_SUPER_USER_ROLE:
            num_admins = await self.user_mgr.count_admins()
            if num_admins == 1:
                raise CsmPermissionDenied(
                    "Cannot delete the last admin user", USERS_MSG_PERMISSION_DENIED, user_id)
        loggedin_user = await self.user_mgr.get(loggedin_user_id)
        if loggedin_user.role != const.CSM_SUPER_USER_ROLE:
            if user_id.lower() != loggedin_user_id.lower():
                raise CsmPermissionDenied("Normal user cannot delete other user",
                                          USERS_MSG_PERMISSION_DENIED, user_id)

        await self.user_mgr.delete(user.user_id)
        return {"message": "User Deleted Successfully."}

    async def _validate_user_update(
        self, user: User, loggedin_user: User,
        password: Optional[str], current_password: Optional[str],
        role: Optional[str]
    ) -> None:
        """
        Check the user update is possible.

        Apply update rules for different user roles. Throw an exception in case of violation,
        otherwise pass.
        :param user: user to be updated.
        :param loggedin_user: user who triggered the update.
        :param password: the new password value.
        :param current_password: user's current password.
        :param role: the new role value.
        :returns: None.
        """
        user_role = user.role
        loggedin_user_role = loggedin_user.role
        self_update = user.user_id == loggedin_user.user_id

        if password:
            allowed = CSM_USER_PASSWD_UPDATE_RULES[loggedin_user_role][user_role].apply(self_update)
            if not allowed:
                msg = f'{loggedin_user.user_id} can not update the password for {user.user_id}'
                raise CsmPermissionDenied(msg, USERS_MSG_UPDATE_NOT_ALLOWED)

        if role:
            allowed = CSM_USER_ROLE_UPDATE_RULES[loggedin_user_role][user_role].apply(self_update)
            if not allowed:
                msg = f'{loggedin_user.user_id} can not update the role for {user.user_id}'
                raise CsmPermissionDenied(msg, USERS_MSG_UPDATE_NOT_ALLOWED)

            # Run additional roles check
            if loggedin_user_role == const.CSM_SUPER_USER_ROLE:
                # Do not downgrade the last admin's role
                # so that the system won't be left without any admin user
                if self_update:
                    num_admins = await self.user_mgr.count_admins()
                    if num_admins == 1:
                        msg = "Cannot change role for the last admin user"
                        raise CsmPermissionDenied(msg, USERS_MSG_UPDATE_NOT_ALLOWED, user.user_id)
            else:
                # Prohibit raising role to admin for other users
                if role == const.CSM_SUPER_USER_ROLE:
                    msg = 'Can not update role to admin'
                    raise InvalidRequest(msg, USERS_MSG_UPDATE_NOT_ALLOWED)

        # Enforce the password check for self-updating the user
        if self_update:
            if current_password is None:
                msg = 'The current password is missing'
                raise InvalidRequest(msg, USERS_MSG_UPDATE_NOT_ALLOWED)
            if not Passwd.verify(current_password, user.password_hash):
                msg = 'The current password is not valid'
                raise InvalidRequest(msg, USERS_MSG_UPDATE_NOT_ALLOWED)

    async def update_user(self, user_id: str, new_values: dict, loggedin_user_id: str) -> dict:
        """
        Update user .
        """
        Log.debug(f"Update user service user_id: {user_id}.")
        user = await self.user_mgr.get(user_id)
        if not user:
            raise CsmNotFoundError(f"User does not exist: {user_id}", USERS_MSG_USER_NOT_FOUND)

        password = new_values.get(const.PASS, None)
        current_password = new_values.get(const.CSM_USER_CURRENT_PASSWORD, None)
        role = new_values.get('role', None)

        loggedin_user = await self.user_mgr.get(loggedin_user_id)
        await self._validate_user_update(user, loggedin_user, password, current_password, role)

        user.update(new_values)
        await self.user_mgr.save(user)
        return self._user_to_dict(user)
