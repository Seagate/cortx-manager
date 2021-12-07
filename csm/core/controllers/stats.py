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

from .view import CsmView, CsmAuth
from cortx.utils.log import Log
from csm.common.permission_names import Resource, Action



#@atomic
@CsmView._app_routes.view("/api/v1/stats/{panel}")
@CsmView._app_routes.view("/api/v2/stats/{panel}")
class StatsView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["stat_service"]
        self._service_dispatch = {
            "get": self._service.get
        }

    """
    GET REST implementation for Statistics request
    """
    @CsmAuth.permissions({Resource.STATS: {Action.LIST}})
    @CsmView.asyncio_shield
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
            metric_list = self.request.rel_url.query.getall("metric", [])
            interval = self.request.rel_url.query.get("interval", "")
            total_sample = self.request.rel_url.query.get("total_sample", "")
            output_format = self.request.rel_url.query.get("output_format", "gui")
            query = self.request.rel_url.query.get("query", "")
            unit = self.request.rel_url.query.get("unit", "")
            return await self._service.get(stats_id, panel, from_t, to_t, metric_list,
                interval, total_sample, unit, output_format, query)

@CsmView._app_routes.view("/api/v1/stats")
@CsmView._app_routes.view("/api/v2/stats")
class StatsPanelListView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["stat_service"]

    @CsmAuth.permissions({Resource.STATS: {Action.LIST}})
    async def get(self):
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
        Log.debug(f"Handling Stats Get Panel List request."
                  f" user_id: {self.request.session.credentials.user_id}")
        panelsopt = self.request.rel_url.query.getall("panel", None)
        metricsopt = self.request.rel_url.query.getall("metric", None)
        if panelsopt or metricsopt:
            stats_id = self.request.rel_url.query.get("id", None)
            from_t = self.request.rel_url.query.get("from", None)
            to_t = self.request.rel_url.query.get("to", None)
            interval = self.request.rel_url.query.get("interval", "")
            total_sample = self.request.rel_url.query.get("total_sample", "")
            output_format = self.request.rel_url.query.get("output_format", "gui")
            if panelsopt:
                Log.debug(f"Stats controller: Panels: {panelsopt}, from: {from_t}, to: {to_t}, "
                          f"interval: {interval}, total_sample: {total_sample}")
                return await self._service.get_panels(stats_id, panelsopt, from_t,
                                                      to_t, interval, total_sample, output_format)
            else:
                Log.debug(f"Stats controller: metric: {metricsopt}, total_sample: {total_sample}, "
                          f"interval: {interval}, from: {from_t}, to: {to_t}")
                return await self._service.get_metrics(stats_id, metricsopt, from_t, to_t,
                                                       interval, total_sample, output_format)
        else:
            Log.debug("Handling Stats Get Panel List request")
            return await self._service.get_panel_list()

@CsmAuth.public
@CsmView._app_routes.view("/api/v2/metrics/stats/perf")
class MetricsView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["stat_service"]
    @CsmAuth.permissions({Resource.STATS: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling Metrics")
        return await self._service.get_perf_metrics()