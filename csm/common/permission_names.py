#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          permission_names.py
 Description:       Permission resources and actions names as constants.

 Creation Date:     02/10/2020
 Author:            Oleg Babin
 
 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


class R:
    ''' Resource Names '''

    ALERT = 'alert'
    USER = 'user'
    STAT = 'stat'
    S3ACCOUNT = 's3account'
    S3USER = 's3user'


class A:
    ''' Action Names '''

    LIST = 'list'
    CREATE = 'create'
    DELETE = 'delete'
    UPDATE = 'update'
