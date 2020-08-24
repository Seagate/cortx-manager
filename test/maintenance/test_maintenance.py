# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import sys
import os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed
from eos.utils.log import Log
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
    try:
        status = _loop.run_until_complete(_maintenance.get_status(node=None))
        if status.get("node_status"):
            Log.console(status)
        else:
            raise TestFailed("Node status test failed")
    except Exception as e:
        raise TestFailed(f"Node status test failed: {e}")

def stop(args):
    """
    Stop all nodes from cluster
    """
    Log.console('Testing node stop ...')
    _maintenance, _loop = TestMaintenanceAppService.init()
    try:
        status = _loop.run_until_complete(_maintenance.stop("srvnode-1"))
        if status.get("message", None):
            Log.console(status)
        else:
            raise TestFailed("stop test failed")
    except Exception as e:
        raise TestFailed(f"stop test failed: {e}")

def start(args):
    """
    Start all nodes from cluster
    """
    Log.console('Testing node start ...')
    _maintenance, _loop = TestMaintenanceAppService.init()
    try:
        status = _loop.run_until_complete(_maintenance.start("srvnode-1"))
        if status.get("message", None):
            Log.console(status)
        else:
            raise TestFailed("start test failed")
    except Exception as e:
        raise TestFailed(f"start test failed: {e}")

def shutdown(args):
    """
    Start all nodes from cluster
    """
    Log.console('Testing node shutdown ...')
    _maintenance, _loop = TestMaintenanceAppService.init()
    try:
        status = _loop.run_until_complete(_maintenance.shutdown("srvnode-1"))
        if status.get("message", None):
            Log.console(status)
        else:
            raise TestFailed("shutdown test failed")
    except Exception as e:
        raise TestFailed(f"shutdown test failed: {e}")

test_list = [ nodes_status, stop, start, shutdown ]
