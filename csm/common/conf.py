#!/usr/bin/env python3

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
import os
from csm.common.payload import *
from csm.common.errors import CsmError

class Conf:
    ''' Represents conf file - singleton '''
    _payloads = {}

    @staticmethod
    def init():
        ''' Initializes data from conf file '''
        pass

    @staticmethod
    def load(index, doc, force=False):
        if not os.path.isfile('%s' %doc):
            raise CsmError(-1, 'File %s does not exist' %doc)
        if index in Conf._payloads.keys():
            if force == False:
                raise Exception('index %s is already loaded')
            Conf.save(index)
        Conf._payloads[index] = Payload(doc)

    @staticmethod
    def get(index, key, default_val=None):
        ''' Obtain value for the given key '''
        return Conf._payloads[index].get(key) \
            if default_val is None else default_val

    @staticmethod
    def set(index, key, val):
        ''' Sets the value into the conf for the given key '''
        Conf._payloads[index].set(key, val)

    @staticmethod
    def save(index=None):
        indexes = [x for x in _payloads.keys()] if index is None else index
        for index in indexes:
            Conf._payloads[index].dump()
