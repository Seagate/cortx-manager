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
from csm.core.blogic.models import CsmModel
from datetime import datetime
from schematics.types import (StringType, DateTimeType,
                              DictType, ListType)

class SessionModel(CsmModel):
    """ Session Model data """

    _id = "_session_id"
    _session_id = StringType()
    _expiry_time = DateTimeType()
    _user_id = StringType()
    _permission = DictType(ListType(StringType))

    @staticmethod
    def instantiate_session(session_id: str,
                expiry_time: datetime,
                user_id: str,
                permissions: {}):
        session = SessionModel()
        session._session_id = session_id
        session._expiry_time = expiry_time
        session._user_id = user_id
        session._permission = permissions
        return session
