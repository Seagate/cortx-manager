#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          validators.py
 Description:       This File will serve as Command Validators for CSM

 Creation Date:     20/11/2019
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from marshmallow.validate import Validator, ValidationError
import re
from csm.core.blogic import const


class StartsWith(Validator):
    def __init__(self, startswith, none_allowed=False):
        self._startswith = startswith
        self._none_allowed = none_allowed

    def __call__(self, value):
        if not value and self._none_allowed:
            return value
        if not value.startswith(self._startswith):
            raise ValidationError(f"Value Must Start with {self._startswith}")
        return value

class Password(Validator):

    def __call__(self, password):
        if len(password) < 8:
            raise ValidationError(
                "Password must be of more than 8 characters.")
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                "Password must contain at least one Uppercase Alphabet.")
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                "Password must contain at least one Lowercase Alphabet.")
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                "Password must contain at least one Numeric value.")
        if not re.search(r"[" + "\\".join(const.PASSWORD_SPECIAL_CHARACTER) + "]",
                         password):
            raise ValidationError(
                f"Password must include at lease one of the {''.join(const.PASSWORD_SPECIAL_CHARACTER)} characters.")
