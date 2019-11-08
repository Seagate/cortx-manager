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

import aiohttp
import asyncio
from string import Template

from csm.common.conf import Conf
from csm.core.blogic import const
from csm.common.log import Log
from csm.common.errors import CsmError, CsmInternalError
from csm.common.payload import *

#TODO: Convert json to more redable format and add parser to convert data

class TimeSeriesProvider:
    def __init__(self):
        pass

    async def process_request(self, **args):
        pass

class TimelionProvider(TimeSeriesProvider):
    ''' Api for Timelion '''

    def __init__(self):
        ''' Initializes data from conf file '''
        self._url = Conf.get(const.CSM_GLOBAL_INDEX, 'STATS.PROVIDER.url')
        self._header = const.TIMELION_HEADER
        self._timelion_req_body = Template(const.TIMELION_BODY)
        self._stats_metrics = const.STATS_METRIC_LIST
        with open(const.AGGREGATION_RULE, 'r') as stats_aggr:
            self._aggr_rule = json.loads(stats_aggr.read())

    async def process_request(self, stats_id, panel, from_t, duration_t,
                    metric_list=[], interval="auto",
                    output_format="gui", query=""):
        try:
            res = await self._aggregate_metric(panel, from_t, duration_t,
                                            interval, metric_list, query)
            return await self._convert_payload(res, stats_id, panel, output_format)
        except CsmInternalError as e:
            Log.debug("Failed to request stats %s" %e)
            return {"id": stats_id, "Error": e}

    async def _aggregate_metric(self, panel, from_t, duration_t,
                                    interval, metric_list, query):
        """
        Use aggregation rule to create query to timelion
        """
        if panel.lower() not in self._aggr_rule:
            raise CsmInternalError("Invalid panel request for stats %s"  %panel)
        aggr_panel = self._aggr_rule[panel.lower()]
        if len(metric_list) == 0:
            metric_list = self._stats_metrics[panel.lower()]
        if query is "":
            query = '('
            for metric in metric_list:
                if metric not in aggr_panel:
                    raise CsmInternalError("Invalid operation %s for %s" %(metric,panel))
                query = query + aggr_panel[metric] + ','
            query = query[:-1] + ')'

        body = self._timelion_req_body.substitute(query=query, from_t=from_t,
                                        interval=interval, to_t=duration_t)
        Log.debug("Request to timelion: %s" %body)
        return await self._query(json.loads(body))

    async def _query(self, data):
        ''' Use timelion api to get aggregated data '''
        Log.debug("Creating session request to timelion")
        async with aiohttp.ClientSession() as session:
            async with session.post(self._url,
                        json=data,
                        headers=self._header) as resp:
                result = await resp.text()
            await session.close()
        return result

    async def _convert_payload(self, res, stats_id, panel, output_format):
        """
        Convert timelion response to redable or gui format
        """
        timelion_payload = json.loads(res)
        res_payload = {}
        li = []
        res_payload['id'] = stats_id
        res_payload['stats'] = panel
        if "sheet" in timelion_payload:
            for s in timelion_payload["sheet"][0]["list"]:
                if output_format == "gui":
                    datapoint = await self._get_list(s['data'])
                elif output_format == "readable":
                    datapoint = s['data']
                operation_stats = { 'data' : datapoint, 'label': str(s["label"]) }
                li.append(operation_stats)
        else:
            raise CsmInternalError(timelion_payload['message'])
        res_payload["list"] = li
        return json.dumps(res_payload)

    async def _get_list(self, li):
        """
        Utility function to cover datapoint gui redable
        """
        total_li = []
        time_li = []
        data_li = []
        if len(li) > 0:
            li.pop(0)
        for item in li:
            time_li.append(item[0])
            data_li.append(item[1])

        total_li.append(time_li)
        total_li.append(data_li)
        return total_li
