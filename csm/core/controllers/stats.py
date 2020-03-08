#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          stats.py
 Description:       Implementation of stats view

 Creation Date:     10/16/2019
 Author:            Naval Patel
                    Eduard Aleksandrov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from .view import CsmView
from csm.common.log import Log

@CsmView._app_routes.view("/api/v1/stats/{panel}")
class StatsView(CsmView):
    def __init__(self, request):
        super(StatsView, self).__init__(request)
        self._service = self.request.app["stat_service"]
        self._service_dispatch = {
            "get": self._service.get
        }

    """
    GET REST implementation for Statistics request
    """
    async def get(self):
        """Calling Stats Get Method"""
        Log.debug(f"Handling get stats request {self.request.rel_url.query}. "
                  f"user_id: {self.request.session.credentials.user_id}")
        getopt = self.request.rel_url.query.get("get", None)
        panel = self.request.match_info["panel"]
        if getopt == "label":
            return await self._service.get_labels(panel)
        elif getopt == "axis_unit":
            return await self._service.get_axis(panel)
        else:
            stats_id = self.request.rel_url.query.get("id", None)
            from_t = self.request.rel_url.query.get("from", None)
            to_t = self.request.rel_url.query.get("to", None)
            metric_list = self.request.rel_url.query.get("metric", [])
            interval = self.request.rel_url.query.get("interval", "")
            total_sample = self.request.rel_url.query.get("total_sample", "")
            output_format = self.request.rel_url.query.get("output_format", "gui")
            query = self.request.rel_url.query.get("query", "")
            unit = self.request.rel_url.query.get("unit", "")
            return await self._service.get(stats_id, panel, from_t, to_t, metric_list.split(","),
                interval, total_sample, unit, output_format, query)

@CsmView._app_routes.view("/api/v1/stats")
class StatsPanelListView(CsmView):
    def __init__(self, request):
        super(StatsPanelListView, self).__init__(request)
        self._service = self.request.app["stat_service"]
    """
    GET REST implementation for Statistics Get Panel List or
             statistics for group of panels with common parameters
    Sample request:
        /api/v1/stats - to get list of panels

        /api/v1/stats?panel=throughput&panel=iops&panel=latency&interval=10&
           from=1579173672&to=1579173772&id=1 - to get statistics for throughput, iops and
                                                latency panels, reduced set of parameters used:
                                                    required: id, from, to, interval
                                                    optional: output_format

        /api/v1/stats?metric=throughput.read&metric=iops.read_object&
           metric=iops.write_object&metric=latency.delete_object&interval=10&
           from=1579173672&to=1579173772&id=1&output_format=gui
           - to get statistics for:
           * throughput metric read,
           * iops metric read_object and write_object,
           * latency metric delete_object,
             reduced set of parameters used, same as aboove
    """
    async def get(self):
        """Calling Stats Get Method"""
        Log.debug(f"Handling Stats Get Panel List request."
                  f" user_id: {self.request.session.credentials.user_id}")
        panelsopt = self.request.rel_url.query.get("panel", None)   # check if statistics requested
        metricsopt = self.request.rel_url.query.get("metric", None)  # check if metric requested
        if panelsopt or metricsopt:
            stats_id = self.request.rel_url.query.get("id", None)
            from_t = self.request.rel_url.query.get("from", None)
            to_t = self.request.rel_url.query.get("to", None)
            interval = self.request.rel_url.query.get("interval", "")
            total_sample = self.request.rel_url.query.get("total_sample", "")
            output_format = self.request.rel_url.query.get("output_format", "gui")
            if panelsopt:
                panels_list = panelsopt.split(",")
                Log.debug("Requested panels: %s", str(panels_list))
                return await self._service.get_panels(stats_id, panels_list, from_t, to_t,
                                                      interval, total_sample, output_format)
            else:
                metrics_list = metricsopt.split(",")
                Log.debug("Requested metrics: %s", str(metrics_list))
                return await self._service.get_metrics(stats_id, metrics_list, from_t, to_t,
                                                       interval, total_sample, output_format)
        else:
            Log.debug("Handling Stats Get Panel List request")
            return await self._service.get_panel_list()
