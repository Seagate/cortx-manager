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

import sys, os
import time
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.common.timeseries import TimelionProvider
from csm.core.blogic import const
from csm.common.log import Log

class TestTimelionProvider:
    def __init__(self):
        self._time_series = TimelionProvider(const.AGGREGATION_RULE)
        self._time_series.init()
        self._loop = asyncio.get_event_loop()

    def get_panels(self):
        return self._loop.run_until_complete(self._time_series.get_panels())

    def process_request(self, args):
        return self._loop.run_until_complete(
                self._time_series.process_request(**args))

def init(args):
    pass

#################
# Tests
#################
def test1(args):
    """
    Use timelion provider to initalize csm
    """
    tp = TestTimelionProvider()

    Log.console('Testing stats provider ...')
    to_t = int(time.time()) - 60
    from_t = int(time.time()) - 120
    req_param = { "stats_id": 1, "panel": "",
                "from_t": from_t, "duration_t": to_t,
                "metric_list": [], "interval": 10,
                "output_format": "gui", "query": ""}

    panels = tp.get_panels()
    for panel in panels:
        req_param["panel"] = panel
        res = tp.process_request(req_param)

test_list = [ test1 ]
