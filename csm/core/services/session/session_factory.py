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

from typing import Optional
from cortx.utils.data.db.db_provider import DataBaseProvider
from csm.core.blogic import const
from cortx.utils.data.access import Query
from cortx.utils.data.access.filters import Compare
from csm.core.services.permissions import PermissionSet
from datetime import datetime, timezone
from csm.core.data.models.session import SessionModel
from csm.common.errors import CsmInternalError
from cortx.utils.conf_store.conf_store import Conf

class SessionCredentials:
    """ Base class for a variying part of the session
    depending on the user type (CSM, LDAP, S3).
    """

    def __init__(self, user_id: str) -> None:
        """
        Instantiation Method for SessionCredentials class
        """
        self._user_id = user_id

    @property
    def user_id(self) -> str:
        return self._user_id


class LocalCredentials(SessionCredentials):
    """ CSM local user specific session credentials - empty """

    def __init__(self, user_id: str, user_role: str) -> None:
        """
        Instantiation Method for LocalCredentials class
        """
        super().__init__(user_id)
        self._user_role = user_role

    @property
    def user_role(self) -> str:
        return self._user_role


class Session:
    """ Session data """

    Id = str
    _id = "_session_id"

    def __init__(self, session_id: Id,
                 expiry_time: datetime,
                 credentials: SessionCredentials,
                 permissions: PermissionSet) -> None:
        """
        Instantiation Method for LocalCredentials class
        """
        self._session_id = session_id
        self._expiry_time = expiry_time
        self._credentials = credentials
        self._permissions = permissions

    @property
    def session_id(self) -> Id:
        return self._session_id

    @property
    def expiry_time(self) -> datetime:
        return self._expiry_time

    @expiry_time.setter
    def expiry_time(self, expiry_time):
        self._expiry_time = expiry_time

    @property
    def credentials(self) -> SessionCredentials:
        return self._credentials

    @property
    def permissions(self) -> PermissionSet:
        return self._permissions

    def get_user_role(self) -> Optional[str]:
        creds = self._credentials
        return creds.user_role if isinstance(creds, LocalCredentials) else None

    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.now(timezone.utc) > self._expiry_time


class InMemory:
    def __init__(self):
        """
        Instantiation Method for InMemory class
        """
        self._stg = {}

    async def delete(self, session_id: Session.Id) -> None:
        self._stg.pop(session_id)

    async def get(self, session_id: Session.Id) -> Optional[Session]:
        return self._stg.get(session_id, None)

    async def get_all(self):
        return list(self._stg.values())

    async def store(self, session: Session) -> None:
        self._stg[session.session_id] = session

class Database:
    def __init__(self, storage: DataBaseProvider):
        """
        Instantiation Method for Database class
        """
        if storage is None:
            raise CsmInternalError("Database Provider is NULL")
        self.storage = storage

    async def convert_model_to_session(self, session_model_list):
        session_list = []
        for model in session_model_list:
            session = Session(model._session_id,
                              model._expiry_time,
                              LocalCredentials(model._user_id, model._user_role),
                              PermissionSet(model._permission))
            session_list.append(session)
        return session_list

    async def convert_session_to_model(self, session:Session):
        sessionModel = SessionModel.instantiate_session(session._session_id, session._expiry_time,
                                                        session._credentials._user_id,
                                                        session._credentials._user_role,
                                                        session._permissions._items)
        return sessionModel

    async def delete(self, session_id: Session.Id) -> None:
        await self.storage(SessionModel).delete(Compare(SessionModel._session_id, '=', session_id))

    async def get(self, session_id: Session.Id) -> Optional[Session]:
        query = Query().filter_by(Compare(SessionModel._session_id, '=', session_id))
        session__model_list = await self.storage(SessionModel).get(query)
        # Storage get() -> param query: session id
        # returns empty list or list with session model object which satisfy the passed query condition

        session_list = await self.convert_model_to_session(session__model_list)
        if session_list:
            return session_list[0]
        else:
            return None

    async def get_all(self):
        # Convert SessionModel to Session
        query = Query()
        session__model_list = await self.storage(SessionModel).get(query)
        session_list = await self.convert_model_to_session(session__model_list)
        return session_list

    async def store(self, session: Session) -> None:
        # Convert session to SessionModel
        sessionModel = await self.convert_session_to_model(session)
        await self.storage(SessionModel).store(sessionModel)

class SessionFactory:
    @staticmethod
    def get_instance(storage: DataBaseProvider=None):
        # session_backend_keys: Two Level nested map
        # First Level Storage : Local / Persistent
        # Inner Level(leaf) backend : add here for more session backend option
        session_backend_keys = {
            const.LOCAL: {
                const.IN_MEMORY : InMemory()
            },
            const.PERSISTENT: {
                const.DB : Database(storage)
            }
        }
        try:
            # Reading Config file for storage and backend
            storage = Conf.get(const.CSM_GLOBAL_INDEX, const.SESSION_STORAGE_KEY)
            backend = Conf.get(const.CSM_GLOBAL_INDEX, const.SESSION_BACKEND_KEY)
            storage_backend = session_backend_keys[storage][backend]
        except:
            raise CsmInternalError("Unable to get Session")
        return storage_backend
