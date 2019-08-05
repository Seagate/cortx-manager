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
from csm.common.payload import *
from csm.common.errors import CsmError

class Conf:
    ''' Represents conf file - singleton '''
    _payload_dict = {}

    @staticmethod
    def init():
        ''' Initializes data from conf file '''
        pass

    @staticmethod
    def load(index, doc):
        if not os.path.isfile('%s' %doc):
            raise CsmError(-1, 'File %s does not exist' %doc)
        Conf._payload_dict[index] = Payload(doc)

    @staticmethod
    def get(index, key, default_val=None):
        ''' Obtain value for the given key '''
        return Conf._payload_dict[index].get(key) \
            if default_val is None else default_val

    @staticmethod
    def set(session, key, val):
        ''' Sets the value into the conf for the given key '''
        Conf._payload_dict[session].set(key, val)

    @staticmethod
    def save(index=None):
        indexes = [x for x in _payload_dict.keys()] if index is None else index
        for index in indexes:
            Conf._payload_dict[index].dump()
