#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          conf.py
 Description:       Contains the configuration handling for CSM

 Creation Date:     31/05/2018
 Author:            Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os, errno
import sys
from csm.common.payload import *
from csm.common.errors import CsmError

class Conf:
    ''' Represents conf file - singleton '''
    _payload_dict = {}


    @staticmethod
    def init(doc, session):
        ''' Initializes data from conf file '''
        if not os.path.isfile('%s' %doc):
            raise CsmError(-1, 'conf file %s does not exist' %doc)
        if session not in Conf._payload_dict.keys():
            Conf._payload_dict[session] = Payload(doc)

    @staticmethod
    def get(session, key, default_val=None):
        ''' Obtain value for the given key '''
        return default_val if default_val is not None else Conf._payload_dict[session].get(key)

    @staticmethod
    def set(session, key, val):
        ''' Sets the value into the conf for the given key '''
        Conf._payload_dict[session].set(key, val)

    @staticmethod
    def save():
        Conf._payload_dict[session].dump()
