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

import sys
import json
import bcrypt
from schematics.models import Model
from schematics.types import (StringType, ListType,
                              DateTimeType, BooleanType)
from datetime import datetime, timedelta, timezone
from csm.common.queries import SortBy, QueryLimits, DateTimeRange
from typing import Optional, Iterable
from enum import Enum
from csm.common.errors import CsmError, CsmNotFoundError
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.core.blogic.models import CsmModel

# TODO: move to the appropriate location
class Passwd:

    @staticmethod
    def hash(password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('ascii')

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('ascii'))


class UserType(Enum):
    CsmUser = "csm"
    LdapUser = "ldap"
    S3AccountUser = "s3_account"


class User(CsmModel):
    _id = "user_id"

    user_id = StringType()
    user_type = StringType()
    roles = ListType(StringType)
    password_hash = StringType()
    email = StringType()
    alert_notification = BooleanType()
    updated_time = DateTimeType()
    created_time = DateTimeType()

    def update(self, new_values: dict):
        if 'password' in new_values:
            self.password_hash = Passwd.hash(new_values['password'])
            new_values.pop('password')
        for key in new_values:
            setattr(self, key, new_values[key])

        self.updated_time = datetime.now(timezone.utc)

    @staticmethod
    def instantiate_csm_user(user_id, password, email="", roles=[], alert_notification=True):
        user = User()
        user.user_id = user_id
        user.user_type = UserType.CsmUser.value
        user.password_hash = Passwd.hash(password)
        user.roles = roles
        user.email = email
        user.alert_notification = alert_notification
        user.created_time = datetime.now(timezone.utc)
        user.updated_time = datetime.now(timezone.utc)
        return user

    @staticmethod
    def instantiate_s3_account_user(user_id, roles=[]):
        user = User()
        user.user_id = user_id
        user.user_type = UserType.S3AccountUser.value
        user.password_hash = None
        user.roles = roles
        user.email = ""
        user.alert_notification = True
        user.created_time = datetime.now(timezone.utc)
        user.updated_time = datetime.now(timezone.utc)
        return user
