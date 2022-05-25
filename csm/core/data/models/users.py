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

import bcrypt
from schematics.types import (StringType, DateTimeType, BooleanType)
from datetime import datetime, timezone
from enum import Enum
from csm.core.blogic import const
from csm.core.blogic.models.base import CsmModel


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
    user_role = StringType()
    user_password = StringType()
    email_address = StringType()
    reset_password = BooleanType()
    alert_notification = BooleanType()
    updated_time = DateTimeType()
    created_time = DateTimeType()

    def update(self, new_values: dict):
        if 'password' in new_values:
            self.user_password= Passwd.hash(new_values['password'])
            new_values.pop('password')
        for key in new_values:
            setattr(self, key, new_values[key])

        self.updated_time = datetime.now(timezone.utc)

    @staticmethod
    def instantiate_csm_user(
        user_id, password, email="", role=const.CSM_MONITOR_ROLE, reset_password = False, alert_notification=True
    ):
        user = User()
        user.user_id = user_id
        user.user_type = UserType.CsmUser.value
        user.user_password = Passwd.hash(password)
        user.user_role = role
        user.email_address = email
        user.alert_notification = alert_notification
        user.reset_password = reset_password
        user.created_time = datetime.now(timezone.utc)
        user.updated_time = datetime.now(timezone.utc)
        return user

    @staticmethod
    def instantiate_s3_account_user(user_id, role=const.CSM_S3_ACCOUNT_ROLE):
        user = User()
        user.user_id = user_id
        user.user_type = UserType.S3AccountUser.value
        user.user_password = None
        user.user_role = role
        user.email_address = ""
        user.alert_notification = True
        user.reset_password = None
        user.created_time = datetime.now(timezone.utc)
        user.updated_time = datetime.now(timezone.utc)
        return user
