#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          run_log.py
 _description:      Logger Reference

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.log import Log

def init(args):
    pass

def test1_1(args={}):
    Log.init('csm', '/tmp', Log.DEBUG)
    Log.debug('test1_1: hello world')
    Log.info('test1_1: hello world')

def test1_2(args={}):
    Log.init('csm', '/tmp', Log.INFO)
    Log.debug('test1_2: hello world')
    Log.info('test1_2: hello world')

test_list = [ test1_1, test1_2 ]
