#!/usr/bin/env python3

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

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.conf import Conf
from csm.core.blogic import const

def init(args):
    pass

def test1(args={}):
    val = Conf.get('dummy', 'default')
    return True if val == 'default' else False

def test2(args={}):
    val = Conf.get(const.INVENTORY_FILE, const.DEFAULT_INVENTORY_FILE)
    return True if val == '/etc/csm/cluster.yaml' else False

test_list = [ test1, test2 ]
