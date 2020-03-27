#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_timelion_provider.py
 Description:       Test timelion provider for csm.

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

import sys
import os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed
from csm.common.log import Log
from core.services.maintenance import MaintenanceAppService
from csm.common.ha_framework import PcsHAFramework

class TestMaintenanceAppService:
    def __init__(self):
        pass

    @staticmethod
    def init():
        _maintenance = MaintenanceAppService(PcsHAFramework())
        _loop = asyncio.get_event_loop()
        return _maintenance, _loop

def init(args):
    pass

#################
# Tests
#################
def nodes_status(args):
    """
    Use timelion provider to initalize csm
    """
    _maintenance, _loop = TestMaintenanceAppService.init()
    Log.console('Testing node status ...')
    status = _loop.run_until_complete(_maintenance.get_status(node=None))
    if status:
        Log.console(status)
    else:
        raise TestFailed("Node status test failed")

def stop(args):
    """
    Stop all nodes from cluster
    """
    Log.console('Testing node stop ...')
    _maintenance, _loop = TestMaintenanceAppService.init()
    status = _loop.run_until_complete(_maintenance.stop("all"))
    if "Success" in status["message"]:
        Log.console(status)
    else:
        raise TestFailed("stop test failed")

def start(args):
    """
    Start all nodes from cluster
    """
    Log.console('Testing node start ...')
    _maintenance, _loop = TestMaintenanceAppService.init()
    status = _loop.run_until_complete(_maintenance.start("all"))
    if "Success" in status["message"]:
        Log.console(status)
    else:
        raise TestFailed("start test failed")

test_list = [ nodes_status, stop, start ]
