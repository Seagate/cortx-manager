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
from schematics.types import (StringType, DateTimeType, ModelType,
                              DictType, ListType)

class PermissionSetModel(CsmModel):
    ''' Permission Set Model stored in a compact way as a dictionary '''

    _items = DictType(ListType(StringType))

class SessionCredentialsModel(CsmModel):
    """ Model class for a variying part of the session
    depending on the user type (CSM, LDAP, S3).
    """
    _user_id = StringType()

class SessionModel(CsmModel):
    """ Session data """

    _id = "_session_id"
    _session_id = StringType()
    _expiry_time = DateTimeType()
    _credentials = ModelType(SessionCredentialsModel)
    _permissions = ModelType(PermissionSetModel)

    @staticmethod
    def instantiate_session(session_id: str,
                expiry_time: datetime,
                credentials: SessionCredentialsModel,
                permissions: PermissionSetModel):
        session = SessionModel()
        session._session_id = session_id
        session._expiry_time = expiry_time
        session._credentials = credentials
        session._permissions = permissions
        return session
