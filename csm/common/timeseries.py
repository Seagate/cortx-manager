#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          timeseries.py
 Description:       Query to timeseries apps to aggregate data

 Creation Date:     10/31/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import aiohttp
import asyncio
from string import Template
from datetime import datetime, timedelta

from csm.common.conf import Conf
from csm.core.blogic import const
from eos.utils.log import Log
from csm.common.errors import CsmError, CsmInternalError
from csm.common.payload import *

class TimeSeriesProvider:
    def __init__(self, agg_rule_file):
        self._agg_rule_file = agg_rule_file

    def init(self):
        """
        Parse aggregation rule payload and convert to generic template
        """
        with open(self._agg_rule_file, 'r') as stats_aggr:
            self._agg_rule = json.loads(stats_aggr.read())
        self._template_agg_rule = {}
        for panel in self._agg_rule.keys():
            metrics = {}
            for metric in self._agg_rule[panel]["metrics"]:
                metrics[metric["name"]] = ""
            self._template_agg_rule[panel] = {
                    "axis": self._agg_rule[panel]["axis"],
                    "processing": self._agg_rule[panel]["processing"],
                    "metrics": metrics}
        self._panels = self._template_agg_rule.keys()

    async def get_panels(self):
        """
        Return panels list
        """
        return self._panels

    async def get_metrics(self):
        """
        Return metrics list
        """
        metrics = []
        for panel in self._agg_rule.keys():
            for metric in self._agg_rule[panel]["metrics"]:
                metrics.append(str(panel) + '.' + str(metric.get('name')))

        return metrics

    async def _validate_panel(self, panel):
        """
        Validate panal from aggregation rule
        """
        Log.debug("Validate %s panel"  %panel)
        return True if panel in self._panels else False

    async def get_labels(self, panel):
        """
        Return labels of panels
        """
        if not await self._validate_panel(panel):
            raise CsmInternalError("Invalid panel request for stats %s"  %panel)
        return self._template_agg_rule[panel]["metrics"].keys()

    async def get_axis(self, panel):
        """
        Return x and y axis units
        """
        if not await self._validate_panel(panel):
            raise CsmInternalError("Invalid panel request for stats %s"  %panel)
        return self._template_agg_rule[panel]["axis"]

    async def process_request(self, **args):
        pass

class TimelionProvider(TimeSeriesProvider):
    """
    Api for Timelion
    """

    _SIZE_DIV = {"bytes": 1, "kb": 1024, "mb": 1048576, "gb": 1073741824}

    def __init__(self, agg_rule):
        """
        Initializes data from conf file
        """
        super(TimelionProvider, self).__init__(agg_rule)
        host = Conf.get(const.CSM_GLOBAL_INDEX, 'STATS.PROVIDER.host')
        port = Conf.get(const.CSM_GLOBAL_INDEX, 'STATS.PROVIDER.port')
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, 'STATS.PROVIDER.ssl_check')
        protocol = "https://" if ssl_check else "http://"
        self._url = protocol + host + ":" + str(port) + "/api/timelion/run"
        self._header = { 'Content-Type': 'application/json',
                            'Accept': 'application/json, text/plain, */*',
                            'kbn-xsrf': 'anything',
                            'Connection': 'keep-alive'}
        self._timelion_req_body = Template('{"sheet": [ "$query"], \
                                "time": { \
                                        "from": "$from_t", \
                                        "interval": "$interval", \
                                        "mode":"quick", \
                                        "to":"$to_t" \
                                }}')
        self._timelion_query = Template('.es(q=$metric, timefield=$timestamp, ' +
                                'index=$index, metric=$method).$processing()')

    def init(self):
        try:
            super(TimelionProvider, self).init()
            self._storage_interval = int(Conf.get(const.CSM_GLOBAL_INDEX, 'STATS.PROVIDER.interval'))
            self._offset_interval = int(Conf.get(const.CSM_GLOBAL_INDEX, 'STATS.PROVIDER.offset'))
            self._metric_set = {
                "+": "sum()",
                "/": "divide()"
            }
            self._config_list = {
                "interval": "${interval}"
            }
            for panel in self._agg_rule.keys():
                template_metrics = self._template_agg_rule[panel]["metrics"]
                for metric in self._agg_rule[panel]["metrics"]:
                    query = "(" + self._parse(metric["node"], panel, output="") +\
                                ").label(" + metric["name"] + ")"
                    template_metrics[metric["name"]] = query
            self._aggr_rule = self._template_agg_rule
            self._indexes = ["statsd_timerdata-*", "statsd_counter-*", "statsd_gauge-*"]
        except Exception as e:
            Log.debug("Failed to parse stats aggregation rule %s" %e)
            raise CsmInternalError("Failed to parse stats aggregation rule")

    def _parse(self, nodes, panel, output):
        for node in nodes:
            if type(node["val"]) is str:
                if node["val"] in self._metric_set.keys():
                    output = self._parse(node["node"], panel, output)
                    output = "(" + output + ")." + self._metric_set[node["val"]]
                elif node["val"] in self._config_list.keys():
                    cv = self._config_list[node["val"]]
                    if cv is None:
                        raise CsmInternalError('Can not load config parameter "%s"' %node["val"])
                    output = output[:-1] + str(cv) + ")"
                else:
                    raise CsmInternalError("Invalid value %s " %node["val"])
            elif type(node["val"]) is int:
                output = output[:-1] + str(node["val"]) + ")"
            else:
                if output is "":
                    output = self._parse_query(node["val"], panel)
                else:
                    output = "(" + output + "),(" + self._parse_query(node["val"], panel)+")"
        return output

    def _parse_query(self, val, panel):
        query = self._timelion_query.substitute(
                    index=val["index"],
                    metric=val["metric"],
                    timestamp=val["timestamp"],
                    processing=self._template_agg_rule[panel]["processing"],
                    method=val["method"])
        return query

    async def process_request(self, stats_id, panel, from_t, duration_t,
                    metric_list, interval, total_sample,
                    unit, output_format, query):
        """
        Process request comming from csm stats api
        Parameter:
            stats_id: Request id for aggregation
            panel: Which type metric throughput, iops, etc.
            from_t: Starting time of stats
            duration_t: Ending time of stats
            metric_list: List of labels
            interval: Difference between two datapoint [default: auto]
            output_format: Json format either redable or gui. [default: gui]
            query: Optional direct query to timelion_api
        """
        Log.debug(f"Timelion Request: id: {stats_id}, panel: {panel}, from: {from_t}, "
                  f"duration: {duration_t}, metric_list: {metric_list}, interval: {interval}, "
                  f"total_sample: {total_sample}, unit: {unit}, output_format: {output_format}")
        try:
            interval, duration_t, from_t = await self._parse_interval(from_t, duration_t, interval, total_sample)
            from_t = str(datetime.utcfromtimestamp(int(from_t)).isoformat())+'.000Z'
            duration_t = str(datetime.utcfromtimestamp(int(duration_t)).isoformat())+'.000Z'
            panel = panel.lower()
            metric_list, unit_list = await self._get_metric_list(panel, metric_list, unit)
            res = await self._aggregate_metric(panel, from_t, duration_t,
                                            interval, metric_list, query)
            return await self._convert_payload(res, stats_id, panel, output_format, unit_list)
        except Exception as e:
            Log.debug("Failed to request stats %s" %e)
            raise CsmInternalError("id: %s, Error: Failed to process timelion "
                "request %s" %(stats_id,e))

    async def get_all_units(self):
        """
        Return all combinations of metrics with possible units of measure of each metric
        """
        mu = []
        for panel in self._agg_rule.keys():
            for metric in self._agg_rule[panel]["metrics"]:
                st = (str(panel) + '.' + str(metric.get('name')) + '.'
                       + str((await self.get_axis(panel))["y"]))
                if st not in mu:
                    mu.append(st)
                if panel =="throughput":
                    for sz in self._SIZE_DIV.keys():
                        st = (str(panel) + '.' + str(metric.get('name')) + '.' + str(sz))
                        if st not in mu:
                            mu.append(st)
        return mu

    async def _get_metric_list(self, panel, metric_list, unit):
        """
        Validate metric list. If metric list is empty then fetch from schema.
        Validate and update units.
        """
        aggr_panel = self._aggr_rule[panel]["metrics"]
        panel_unit = (await self.get_axis(panel))["y"]
        unit_li = []
        if type(unit) is list:
            unit_li = unit
        if len(metric_list) == 0:
            metric_list = list(await self.get_labels(panel))
        for i in range(0, len(metric_list)):
            if metric_list[i] not in aggr_panel:
                raise CsmInternalError("Invalid label %s for %s" %(metric,panel))
            if type(unit) is list:
                unit_li[i] = unit[i] if unit[i] != "" else panel_unit
            else:
                u = unit if unit is not "" else panel_unit
                unit_li.append(u)

        return metric_list, unit_li

    async def _parse_interval(self, from_t, duration_t, interval, total_sample):
        """
        Check from_t, duration_t time interval and
        calculate interval from total_sample
        """
        diff_sec = int(duration_t) - int(from_t)
        if diff_sec <= 0:
            raise CsmInternalError("to time should be grater than from time")
        from_t = int(from_t) - int(self._offset_interval)
        duration_t = int(duration_t) - int(self._offset_interval)
        if total_sample == "" and interval == "":
            interval = str(self._storage_interval) + 's'
        elif total_sample != "":
            interval = str(int(diff_sec/int(total_sample))) + 's'
        elif interval != "":
            interval = str(int(interval)) + 's'
        else:
            raise CsmInternalError("Unable to parse interval")
        return interval, duration_t, from_t

    async def _update_index(self, metric, from_t, duration_t):
        """
        Optimize index pattern
        1. from and duration are same date
            from_t:  2020-03-08T14:27:12.000Z
            duration_t: 2020-03-08T14:27:12.000Z
            index: statsd_counter-2020.03.08
        2. from and duration are diff by date
            from_t:  2020-03-08T14:27:12.000Z
            duration_t: 2020-03-09T14:27:12.000Z
            index: statsd_counter-2020.03.*
        3. from and duration are diff by month
            from_t:  2020-02-08T14:27:12.000Z
            duration_t: 2020-03-09T14:27:12.000Z
            index: statsd_counter-2020.*
        4. from and duration are diff by year
            from_t:  2019-03-08T14:27:12.000Z
            duration_t: 2020-03-09T14:27:12.000Z
            index: statsd_counter-*
        """
        old_index = ""
        new_index = ""
        f_li = (from_t.split("T")[0]).split("-")
        d_li = (duration_t.split("T")[0]).split("-")
        for index in self._indexes:
            if index in metric:
                old_index = index
                break
        if f_li == d_li:
            new_index =  old_index.replace("*", '.'.join([ele for ele in f_li]))
        elif f_li[0] == d_li[0] and f_li[1] == d_li[1]:
            new_index = old_index.replace("*", f"{d_li[0]}.{d_li[1]}.*")
        elif f_li[0] == d_li[0]:
            new_index = old_index.replace("*", f"{d_li[0]}.*")
        else:
            new_index = old_index
        metric = metric.replace(old_index,new_index)
        return metric

    async def _aggregate_metric(self, panel, from_t, duration_t,
                                    interval, metric_list, query):
        """
        Use aggregation rule to create query to timelion
        """
        if not await self._validate_panel(panel):
            raise CsmInternalError("Invalid panel request for stats %s"  %panel)
        aggr_panel = self._aggr_rule[panel]["metrics"]
        if query is "":
            query = '('
            for metric in metric_list:
                query = query + await self._update_index(aggr_panel[metric], from_t, duration_t) + ','
            query = query[:-1] + ')'
        body = self._timelion_req_body.substitute(query=query, from_t=from_t,
                                        interval=interval, to_t=duration_t)
        body = body.replace("${interval}", str(interval.replace("s", "")))
        return await self._query(json.loads(body))

    async def _query(self, data):
        """
        Use timelion api to get aggregated data
        """
        try:
            Log.debug("Creating session request to timelion")
            async with aiohttp.ClientSession() as session:
                async with session.post(self._url,
                            json=data,
                            headers=self._header) as resp:
                    result = await resp.text()
                await session.close()
            return result
        except Exception as e:
            Log.debug("Timelion connection error: %s" %e)
            raise CsmInternalError("Connection failed to timelion %s" %self._url)

    async def _convert_payload(self, res, stats_id, panel, output_format, units):
        """
        Convert timelion response to redable or gui format
        """
        timelion_payload = json.loads(res)
        res_payload = {}
        li = []
        res_payload['id'] = stats_id
        res_payload['stats'] = panel
        if "sheet" in timelion_payload:
            data_list = timelion_payload["sheet"][0]["list"]
            for i in range(0, len(data_list)):
                datapoint = await self._modify_panel_val(data_list[i]["data"], panel, units[i])
                if output_format == "gui":
                    datapoint = await self._get_list(datapoint)
                operation_stats = { 'data' : datapoint,
                                    'name': f"{panel}.{str(data_list[i]['label'])}",
                                    'unit': units[i] }
                li.append(operation_stats)
        elif "index not found" in timelion_payload["message"] or \
                "index_not_found_exception" in timelion_payload["message"]:
            pass
        else:
            raise CsmInternalError("Failed to convert timelion response. \
                %s" %timelion_payload)
        res_payload["list"] = li
        return res_payload

    async def _modify_panel_val(self, datapoint, panel, unit):
        """
        Preform panel specific operation
        """
        if panel == "throughput":
            datapoint = await self._modify_throughput(datapoint, unit)
        return datapoint

    async def _modify_throughput(self, datapoint, unit):
        """
        Modify throughput with unit
        """
        li = []
        if unit not in self._SIZE_DIV.keys():
            raise CsmInternalError("Invalid unit for stats %s" %unit)
        unit_val = self._SIZE_DIV[unit]
        for point in datapoint:
            val = 0 if point[1] is None or point[1] < 0 else point[1]
            li.append([point[0], val/unit_val])
        return li

    async def _get_list(self, li):
        """
        Utility function to cover datapoint gui redable
        """
        total_li = []
        time_li = []
        data_li = []
        for item in li:
            time_li.append(item[0])
            data_li.append(float("{:.2f}".format(item[1])))

        total_li.append(time_li)
        total_li.append(data_li)
        return total_li
