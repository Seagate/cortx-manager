#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_systemd_service.py
 Description:       Test csm_agent and csm_web status.

 Creation Date:     07/08/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os
import time
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from csm.common.log import Log
from csm.common.errors import CsmError

def init(args):
    pass

#################
# Tests
#################
def test1(args):
    """
    Check status for csm agent service
    """
    Log.console('Testing csm_agent service ...')
    status = os.system("systemctl is-active --quiet csm_agent")
    if status != 0:
        raise CsmError(status, "csm_agent service is not running...")

def test2(args):
    """
    Check status for csm web service
    """
    Log.console('Testing csm_web service ...')
    status = os.system("systemctl is-active --quiet csm_web")
    if status != 0:
        raise CsmError(status, "csm_web service is not running...")

test_list = [ test1, test2 ]
