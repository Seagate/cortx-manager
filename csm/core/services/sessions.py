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

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional
from cortx.utils.log import Log
from cortx.utils.data.db.db_provider import DataBaseProvider
# TODO: from csm.common.passwd import Passwd
from csm.core.data.models.users import UserType, User, Passwd
from csm.core.services.users import UserManager
from csm.core.services.roles import RoleManager
from csm.core.services.permissions import PermissionSet
from csm.common.errors import CsmError, CsmPermissionDenied, CSM_ERR_INVALID_VALUE
from csm.core.services.session.session_factory import (SessionFactory, SessionCredentials,
                                               Session, LocalCredentials)


class LdapCredentials(SessionCredentials):
    """ LDAP user specific session credentials - TBD """

    def __init__(self, user_id: str) -> None:
        super().__init__(user_id)


class S3Credentials(SessionCredentials):
    """ S3 account specific session credentials """

    def __init__(self, user_id: str, access_key: str,
                 secret_key: str, session_token: str) -> None:
        super().__init__(user_id)
        self._access_key = access_key
        self._secret_key = secret_key
        self._session_token = session_token


    @property
    def access_key(self):
        return self._access_key

    @property
    def secret_key(self):
        return self._secret_key

    @property
    def session_token(self):
        return self._session_token

class SessionManager:
    """ Session management class """

    def __init__(self, storage: DataBaseProvider=None):
        """
        Instantiation Method for SessionManager class
        """
        self._expiry_interval = timedelta(minutes=60)  # TODO: Load from config
        self._sessionFactory = SessionFactory.get_instance(storage)

    @property
    def expiry_interval(self):
        return self._expiry_interval

    @staticmethod
    def _generate_sid() -> Session.Id:
        return uuid.uuid4().hex

    def calc_expiry_time(self) -> datetime:
        now = datetime.now(timezone.utc)
        return now + self._expiry_interval

    async def create(self, credentials: SessionCredentials,
                     permissions: PermissionSet) -> Session:
        session_id = self._generate_sid()
        expiry_time = self.calc_expiry_time()
        session = Session(session_id, expiry_time, credentials, permissions)
        await self._sessionFactory.store(session)
        return session

    async def delete(self, session_id: Session.Id) -> None:
        await self._sessionFactory.delete(session_id)

    async def get(self, session_id: Session.Id) -> Optional[Session]:
        return await self._sessionFactory.get(session_id)

    async def get_all(self):
        return await self._sessionFactory.get_all()

    async def update(self, session: Session) -> None:
        await self._sessionFactory.store(session)

    async def clear_sessions(self):
        """
        Entry point for clearing expired token background task
        :return:
        """
        today= datetime.now(timezone.utc).date()
        await self._timer_task(handler=self._remove_expired_sessions,
        start=datetime(today.year, today.month, today.day,tzinfo=timezone.utc),interval=timedelta(hours=2))

    async def _timer_task(self, handler, start: datetime, interval: timedelta):
        """
        Create timer for background task
        :return:
        """
        current = datetime.now(timezone.utc)
        while True:
            delta = (start - current).total_seconds()
            if delta > 0:
                await asyncio.sleep(delta)
            await handler()
            current = datetime.now(timezone.utc)
            start = start + interval

    async def _remove_expired_sessions(self):
        """
        Remove expired sessions from the storage.
        """
        sessions = await self.get_all()
        for s in sessions:
            if s.is_expired():
                await self.delete(s.session_id)

class QuotaSessionManager(SessionManager):
    """Session manager that tracks usage and maintains usage quotas."""

    def __init__(self, storage: DataBaseProvider, active_users_quota: int) -> None:
        """
        Initialize the QuotaSessionManager.

        :param storage: storage for sessions.
        :param active_users_quota: number of users that are allowed to simultaneously use CSM.
        :returns: None.
        """
        super().__init__(storage)
        self._active_users_restored = False
        self._active_users = dict()
        self._active_users_quota = active_users_quota

    async def _restore_active_users(self):
        """Restore active users statistics from the session list."""
        sessions = await self.get_all()
        for s in sessions:
            if s.is_expired():
                await self.delete(s.session_id)
            else:
                await self._add_active_user_with_quota(s.credentials.user_id)

    async def _remove_expired_sessions(self):
        """Remove expired sessions from the storage."""
        # FIXME: support deletion by query for in-memory Session storage and then
        # use query to remove expired items.
        sessions = await self.get_all()
        for s in sessions:
            if s.is_expired():
                await self.delete(s.session_id)

    async def _add_active_user_with_quota(self, user_id: str) -> bool:
        """
        Increment the number of sessions for the user with the provided ID if the quota is not full.

        :param user_id: new session user's ID.
        :returns: True if quota is not full, False otherwise.
        """
        if self._active_users_quota <= 0:
            return True
        if not self._active_users_restored:
            self._active_users_restored = True
            await self._restore_active_users()
        active_users = len(self._active_users)
        overflow = (active_users >= self._active_users_quota)
        # Try to free space by removing expired sessions
        if overflow:
            await self._remove_expired_sessions()
        active_users = len(self._active_users)
        overflow = (active_users > self._active_users_quota)
        if overflow:
            return False
        user_sessions = self._active_users.get(user_id, 0)
        # Active users quota is full and the new user is added.
        if active_users == self._active_users_quota and user_sessions == 0:
            return False
        self._active_users[user_id] = user_sessions + 1
        return True

    def _remove_active_user(self, user_id: str) -> None:
        """
        Decrement the number of sessions for the user with the provided ID.

        :param user_id: removed session user's ID.
        :returns: None.
        """
        user_sessions = self._active_users.get(user_id, 0)
        if user_sessions > 1:
            self._active_users[user_id] = user_sessions - 1
        elif user_sessions == 1:
            del self._active_users[user_id]

    async def create(self, credentials: SessionCredentials, permissions: PermissionSet) -> Session:
        """
        Create a new session followint the quota.

        :param credentials: session credentials.
        :param permissions: session permissions.
        :returns: Session object.
        """
        session = None
        user_id = credentials.user_id
        if await self._add_active_user_with_quota(user_id):
            session = await super().create(credentials, permissions)
        else:
            raise CsmPermissionDenied('Active users quota is reached')
        return session

    async def delete(self, session_id: Session.Id) -> None:
        """
        Delete the session updating quota related statistics.

        :param session_id: session ID.
        :returns: None.
        """
        session = await self.get(session_id)
        user_id = session.credentials.user_id
        await super().delete(session_id)
        self._remove_active_user(user_id)


class AuthPolicy(ABC):
    """ Base abstract class for various authentication policies """

    @abstractmethod
    async def authenticate(self, user: User, password: str) -> Optional[SessionCredentials]:
        pass

class LocalAuthPolicy(AuthPolicy):
    """ Local CSM user authentication policy """

    async def authenticate(self, user: User, password: str) -> Optional[SessionCredentials]:
        if Passwd.verify(password, user.user_password):
            return LocalCredentials(user.user_id, user.user_role)
        return None


class LdapAuthPolicy(AuthPolicy):
    """ Customer LDAP user authentication policy """

    async def authenticate(self, user: User, password: str) -> Optional[SessionCredentials]:
        # ldap_session = LdapAuth(user.user_id, password)
        # if ldap_session:
        #    return LdapCredentials(user.user_id, ldap_session=ldap_session)
        return None


class S3AuthPolicy(AuthPolicy):
    """ S3 account authentication policy """

    async def authenticate(self, user: User, password: str) -> Optional[SessionCredentials]:
        # TODO: leaving the following line commented as an example of how S3 authentication
        # might be implemented in CSM for RGW.
        #
        # cfg = S3ConnectionConfig()
        # # Following keys are deprecated
        # cfg.host = Conf.get(const.CSM_GLOBAL_INDEX, const.IAM_HOST)
        # cfg.port = Conf.get(const.CSM_GLOBAL_INDEX, const.IAM_PORT)
        # cfg.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX, 'S3>max_retries_num')
        # if Conf.get(const.CSM_GLOBAL_INDEX, const.IAM_PROTOCOL) == 'https':
        #     cfg.use_ssl = True

        # Log.debug(f'Authenticating {user.user_id}'
        #           f' with S3 IAM server {cfg.host}:{cfg.port}')
        # s3_conn_obj = S3Plugin()
        # response = await s3_conn_obj.get_temp_credentials(user.user_id, password,
        #                                                   connection_config=cfg)
        # if type(response) is not IamError:
        #     # return temporary credentials
        #     return S3Credentials(user_id=user.user_id,
        #                         access_key=response.access_key,
        #                         secret_key=response.secret_key,
        #                         session_token=response.session_token)

        Log.error(f'Failed to authenticate S3 account {user.user_id}')
        return None


class AuthService:
    """ Generic authentication service. Allows to use different
    authentication policies for different user types. """

    def __init__(self):
        self._policies = {
            UserType.CsmUser.value: LocalAuthPolicy(),
            UserType.LdapUser.value: LdapAuthPolicy(),
            UserType.S3AccountUser.value: S3AuthPolicy(),
        }

    async def authenticate(self, user: User, password: str) -> Optional[SessionCredentials]:
        policy = self._policies.get(user.user_type, None)
        if policy:
            return await policy.authenticate(user, password)
        Log.error(f'Invalid user type {user.user_type}')
        return None


class LoginService:
    """ Login service. Authenticates a user with authentication service
    and creates a new session on login. Deletes existing session on logout.
    Checks for existing valid session on every API call. """

    def __init__(self, auth_service: AuthService,
                 user_manager: UserManager,
                 role_manager: RoleManager,
                 session_manager: SessionManager):
        self._auth_service = auth_service
        self._user_manager = user_manager
        self._role_manager = role_manager
        self._session_manager = session_manager

    async def login(self, user_id, password):
        Log.debug(f'Logging in user {user_id}')

        user = await self._user_manager.get(user_id)

        if user is None:
            Log.error(f"User with ID - {user_id} - does not exist")
            return None, None
        credentials = await self._auth_service.authenticate(user, password)
        if credentials is None:
            Log.error(f'Authentication failed for user: {user_id}')
            return None, None

        # Check if valid session exists
        session = await self._is_valid_session_exists(user_id)
        if not session:
            # if No valid session exists, then create new session
            Log.info(f"[{self.request.request_id}] Session expired, creating new session for user: {user_id}")
            permissions = await self._role_manager.calc_effective_permissions(user.user_role)
            session = await self._session_manager.create(credentials, permissions)
        if not session:
            Log.error(f"[{self.request.request_id}] Failed to create a new session for user: {user_id}")
            return None, None

        return session.session_id, {"reset_password": user.reset_password}

    async def logout(self, session_id):
        Log.debug(f'Logging out session {session_id}.')
        await self._session_manager.delete(session_id)

    async def auth_session(self, session_id: Session.Id) -> Session:
        session = await self._session_manager.get(session_id)
        if not session:
            raise CsmError(CSM_ERR_INVALID_VALUE, f'Invalid session id: {session_id}')
        # Check Expiry Time
        if datetime.now(timezone.utc) > session.expiry_time:
            await self._session_manager.delete(session_id)
            raise CsmError(CSM_ERR_INVALID_VALUE, 'Session expired')
        # Refresh Expiry Time
        session.expiry_time = self._session_manager.calc_expiry_time()
        return session

    async def get_temp_access_keys(self, user_id: str) -> list:
        """
        Gathers temporary S3 access keys for user's active sessions.
        :param user_id: user ID, for S3 session the S3 user name is expected.
        :return: List of temporary access keys.
        """
        sessions = await self._session_manager.get_all()
        return [s.credentials.access_key for s in sessions
                if s.credentials.user_id.lower() == user_id.lower() and isinstance(
                    s.credentials, S3Credentials)]

    async def delete_all_sessions(self, session_id: Session.Id) -> None:
        """
        This Function will delete all the current user's active sessions.
        :param session_id: session_id for user. :type:Str
        :return: None
        """
        session_data = await self._session_manager.get(session_id)
        if session_data:
            user_id = session_data.credentials.user_id
            Log.debug(f"Delete all active sessions for Userid: {user_id}")
            await self.delete_all_sessions_for_user(user_id)
        else:
            await self._session_manager.delete(session_id)

    async def delete_all_sessions_for_user(self, user_id: str) -> None:
        """
        This Function will delete all the current user's active sessions.
        :param user_id: user_id for user. :type:Str
        :return: None
        """
        Log.debug(f"Delete all active sessions for Userid: {user_id}")
        session_data = await self._session_manager.get_all()
        for each_session in session_data:
            if each_session.credentials.user_id.lower() == user_id.lower():
                await self._session_manager.delete(each_session.session_id)

    async def update_session_expiry_time(self, session: Session) -> None:
        session.expiry_time = self._session_manager.calc_expiry_time()
        await self._session_manager.update(session)

    async def _is_valid_session_exists(self, user_id: str) -> None:
        """
        This Function will get the current user's active session.
        :param user_id: user_id for user. :type:Str
        :return: None
        """
        Log.debug(f"Getting active session for user : {user_id}")
        session_data = await self._session_manager.get_all()
        for each_session in session_data:
            if each_session.credentials.user_id.lower() == user_id.lower():
                # Here we get session for active user
                # Check if it is expired,
                if each_session.is_expired():
                    await self._session_manager.delete(each_session.session_id)
                    continue
                Log.debug(f"Got the active sessions for Userid: {user_id}"
                            f"with session id: {each_session.session_id}")
                # Refresh Expiry Time
                await self.update_session_expiry_time(each_session)
                # return valid session
                return each_session
        return None
