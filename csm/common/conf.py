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
import yaml
from csm.common.errors import CsmError

class Conf:
    _map = None

    @staticmethod
    def init(conf_file=None):
        if conf_file is None or not os.path.exists(conf_file):
            Conf._map = {}
            return
        try:
            Conf._map = yaml.load(open(conf_file).read())
        except:
            raise CsmError(errno.ENOENT, 'Unable to read conf from %s' %conf_file)

    @staticmethod
    def get(key, default_value=None):
        if Conf._map == None:
            raise CsmError(errno.ENOENT, 'Configuration not initialized')
        return Conf._map[key] if key in Conf._map else default_value
