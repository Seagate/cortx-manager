"""
 ****************************************************************************
 Filename:          users.py
 Description:       Contains user-related models and definitions

 Creation Date:     11/21/2019
 Author:            Alexander Nogikh
                    Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
import json
import bcrypt
from schematics.models import Model
from schematics.types import IntType, StringType, DateType, ListType, DateTimeType
from datetime import datetime, timedelta, timezone
from csm.common.queries import SortBy, QueryLimits, DateTimeRange
from typing import Optional, Iterable
from enum import Enum
from csm.common.errors import CsmError, CsmNotFoundError
from csm.common.log import Log
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
    interfaces = ListType(StringType)
    roles = ListType(StringType)
    password_hash = StringType()
    temperature = StringType(default=const.CSM_USER_DEFAULT_TEMPERATURE)
    language = StringType(default=const.CSM_USER_DEFAULT_LANGUAGE)
    timeout = IntType(default=const.CSM_USER_DEFAULT_TIMEOUT)
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
    def instantiate_csm_user(user_id, password, interfaces=[], roles=[]):
        user = User()
        user.user_id = user_id
        user.user_type = UserType.CsmUser.value
        user.password_hash = Passwd.hash(password)
        user.roles = roles
        user.interfaces = interfaces
        user.created_time = datetime.now(timezone.utc)
        user.updated_time = datetime.now(timezone.utc)
        return user

    @staticmethod
    def instantiate_s3_account_user(user_id, interfaces=[], roles=[]):
        user = User()
        user.user_id = user_id
        user.user_type = UserType.S3AccountUser.value
        user.password_hash = None
        user.roles = roles
        user.interfaces = interfaces
        user.created_time = datetime.now(timezone.utc)
        user.updated_time = datetime.now(timezone.utc)
        return user
