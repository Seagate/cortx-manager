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

import sys, os
import time
import traceback
import asyncio
# Package statsd removed from csm
# Todo: Code clean up will be covered in future sprint
from statsd import StatsClient

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.services.stats import StatsAppService
from csm.common.timeseries import TimelionProvider
from csm.core.blogic import const
from cortx.utils.log import Log

class TestStatsAppService:
    def __init__(self):
        self._time_series = TimelionProvider(const.AGGREGATION_RULE)
        self._time_series.init()
        self._stats_service = StatsAppService(self._time_series)
        self._loop = asyncio.get_event_loop()

    def dump_data(self):
        c = StatsClient()
        c.timing('create_object_success', 320)
        c.incr("outcoming_object_bytes_count", 200000)
        c.incr("get_object_request_count", 200)

    def get_panels(self):
        return self._loop.run_until_complete(self._time_series.get_panels())

    def get(self, args):
        return self._loop.run_until_complete(self._stats_service.get(**args))

    def get_panel_list(self):
        return self._loop.run_until_complete(self._stats_service.get_panel_list())

    def get_metrics(self, args):
        return self._loop.run_until_complete(self._stats_service.get_metrics(**args))

    def get_panels_stats(self, args):
        return self._loop.run_until_complete(self._stats_service.get_panels(**args))

    def get_labels(self, panel):
        return self._loop.run_until_complete(self._time_series.get_labels(panel))

    def get_axis(self, panel):
        return self._loop.run_until_complete(self._time_series.get_axis(panel))

def init(args):
    args["stats"] = TestStatsAppService()

#################
# Tests
#################

def test1(args):
    """
    Test StatsAppService for single panel
    """
    try:
        tp = args["stats"]
        tp.dump_data()
        time.sleep(10)
        to_t = int(time.time())
        from_t = to_t - 30
        req_param = { "stats_id": 1, "panel": "",
            "from_t": from_t, "to_t": to_t,
            "metric_list": "", "interval": 10,
            "total_sample": "", "unit": "",
            "output_format": "gui", "query": ""
            }
        for panel in tp.get_panels():
            req_param["panel"] = panel
            res = tp.get(req_param)
            Log.console(res)
    except:
        Log.error("Stats: %s" %traceback.format_exc())
        raise TestFailed("Stats Failed for get service")

def test2(args):
    """
    Test stats service to get data of any metric and any panel
    """
    try:
        tp = args["stats"]
        panel_list = tp.get_panel_list()
        from_t = int(time.time()) - 40
        to_t = int(time.time())
        metrics_list = panel_list["metric_list"] + panel_list["unit_list"]

        req_param = { "stats_id": 1, "metrics_list": metrics_list,
                "from_t": from_t, "to_t": to_t,
                "interval": "", "total_sample": 5, "output_format": "gui"}
        res = tp.get_metrics(req_param)
        Log.console(res)
    except:
        Log.error("Stats: %s" %traceback.format_exc())
        raise TestFailed("Stats Failed for get_metrics service")

def test3(args):
    """
    Test stats for panel list
    """
    try:
        tp = args["stats"]
        tp.dump_data()
        time.sleep(10)
        to_t = int(time.time())
        from_t = to_t - 30
        req_param = { "stats_id": 1, "panels_list": tp.get_panels(),
            "from_t": from_t, "to_t": to_t,
            "interval": 10, "total_sample": "",
            "output_format": "gui"
            }
        res = tp.get_panels_stats(req_param)
        Log.console(res)
    except:
        Log.error("Stats: %s" %traceback.format_exc())
        raise TestFailed("Stats Failed for get_panels_stats service")

def test4(args):
    try:
        tp = args["stats"]
        for panel in tp.get_panels():
            Log.console(tp.get_labels(panel))
            Log.console(tp.get_axis(panel))
    except:
        Log.error("Stats: %s" %traceback.format_exc())
        raise TestFailed("Stats Failed for get_panels_stats service")

test_list = [ test1, test2, test3, test4 ]
