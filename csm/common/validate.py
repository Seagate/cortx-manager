#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          validate.py
 Description:       Generic validatior

 Creation Date:     02/21/2020
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

class Validator:
    @staticmethod
    def validate_type(obj, typ, name):
        if type(obj) is not typ:
            raise ValueError(f'Type of {name} should be a {typ.__name__}')

