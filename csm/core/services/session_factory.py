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

from csm.core.services.sessions import Session
from typing import Optional
from cortx.utils.data.db.db_provider import DataBaseProvider
from csm.core.blogic import const
from cortx.utils.data.access import Query
from cortx.utils.data.access.filters import Compare

class InMemory:
    def __init__(self):
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
        self.storage = storage

    async def delete(self, session_id: Session.Id) -> None:
        await self.storage(Session).delete(Compare(Session.Id, '=', session_id))

    async def get(self, session_id: Session.Id) -> Optional[Session]:
        query = Query().filter_by(Compare(Session.Id, '=', session_id))
        return list(await self.storage(Session).get(query))

    async def get_all(self):
        #TODO :- need to verify
        query = Query()
        return list(await self.storage(Session).get(query))

    async def store(self, session: Session) -> None:
        await self.storage(Session).store(session)

class SessionFactory:
    @staticmethod
    def get_session(self, session_backend, storage: DataBaseProvider=None):
        if session_backend == const.DB:
            return Database(storage)
        elif session_backend == const.IN_MEMORY:
            return InMemory()
        else:
            raise ValueError(session_backend)