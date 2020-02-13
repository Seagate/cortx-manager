#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          stats.py
 Description:       Services for stats handling

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


"""
    This is Stats service implementation
"""


# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict
from csm.common.log import Log
from csm.common.services import Service, ApplicationService

STATS_DATA_MSG_NOT_FOUND = "stats_not_found"

class StatsAppService(ApplicationService):
    """
    Provides operations on stats without involving the domain specifics
    """

    def __init__(self, stats_provider):
        self._stats_provider = stats_provider

    async def get(self, stats_id, panel, from_t, to_t,
                  metric_list, interval, total_sample, unit, output_format, query) -> Dict:
        """
        Fetch specific statistics for panel - full parameter set
        :return: :type:list
        """
        Log.debug('Get panel %s directly: id=%s, interval=%s' %(panel, stats_id, interval))
        output = {}
        output["id"]=stats_id
        panel_data =  await self._stats_provider.process_request(stats_id = stats_id, panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = metric_list,
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = unit.lower(),
                                                  output_format = output_format,
                                                  query = query)
        output["metrics"] = await self._metric_convert(None,panel_data)
        return output

    async def get_labels(self, panel):
        """
        Fetch available labels for panel
        """
        label_list_dict_keys = await self._stats_provider.get_labels(panel)
        return {"label_list": list(label_list_dict_keys)}

    async def get_axis(self, panel):
        """
        Fetch axis unit for selected panel
        """
        return {"axis_unit": await self._stats_provider.get_axis(panel)}

    async def get_panel_list(self):
        """
        Fetch Panels and metrics list for use with special metrics requests
        """
        panel_list_dict_keys = await self._stats_provider.get_panels()
        metric_list_dict_keys = await self._stats_provider.get_metrics()
        units_list_dict_keys = await self._stats_provider.get_all_units()
        return {"panel_list": list(panel_list_dict_keys),
                "metric_list": list(metric_list_dict_keys),
                "unit_list": list(units_list_dict_keys)}

    async def get_panels(self, stats_id, panels_list, from_t, to_t, interval,
                         total_sample, output_format) -> Dict:
        """
        Fetch statistics for selected panels list (simplified - reduced parameter set)
        """
        Log.debug('Get panels requested: id=%s, interval=%s' %(stats_id, interval))
        output = {}
        output["id"]=stats_id
        data_list = []
        for panel in panels_list:
            panel_strip = panel.replace('"','')  # strip " symbol if it presents in input
            panel_data = await self._stats_provider.process_request(
                                                  stats_id = stats_id,
                                                  panel = panel_strip,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = [],
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = "",
                                                  output_format = output_format,
                                                  query = "")
            data_list.extend(await self._metric_convert(None,panel_data))
        output["metrics"] =data_list
        return output

    async def _metric_convert(self, uom, in_list):
        output = []
        parent_name = in_list["stats"]
        for p in in_list["list"]:
            prep = {}
            prep["data"] = p["data"]
            prep["name"] = parent_name + '.' + p["label"]
            if uom:
                prep["unit"] = uom
            else:
                prep["unit"] = (await self._stats_provider.get_axis(parent_name))["y"]
            output.append(prep)
        return output

    async def get_metrics(self, stats_id, metrics_list, from_t, to_t, interval,
                          total_sample, output_format) -> Dict:
        """
        Fetch statistics for selected panel.metric list (simplified - reduced parameter set)
        """
        Log.debug('Get metrics requested: id=%s, interval=%s' %(stats_id, interval))
        output = {}
        panel_list = []
        metric_list = {}
        uom_list = {}
        for panel_metric in metrics_list:  # first create list of panels and arrays of metrics for them
            pm_strip = panel_metric.replace('"','')  # strip " symbol if it presents in input
            pm = pm_strip.split('.',2)
            panel = pm[0]
            metric = pm[1]
            if len(pm)>2:
                uom = pm[2]
            else:
                uom = (await self._stats_provider.get_axis(panel))["y"]
            if panel not in panel_list:
                panel_list.append(panel)
            try:
                ml = metric_list.pop(panel)
            except KeyError as e:
                ml = []
            ml.append(metric)
            metric_list[panel] = ml
            if uom_list.get(panel,None) and uom != uom_list[panel]:
                Log.error('Requested different units of measure for one panel[%s], '
                          'assuming %s' %(str(panel),str(uom)))
            uom_list[panel] = uom
        Log.debug('panel_list = %s' %(str(panel_list)))
        output["id"]=stats_id
        data_list = []
        for panel in panel_list:  # now get statistics and remove not needed metrics
            Log.debug('metric_list[%s] = %s' %(str(panel), str(metric_list[panel])))
            panel_data = await self._stats_provider.process_request(
                                                  stats_id = stats_id,
                                                  panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = [],
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = uom_list[panel],
                                                  output_format = output_format,
                                                  query = "")
            m_list = panel_data.get("list")
            panel_data["list"] = [i for i in m_list if i.get("label") in metric_list.get(panel)]
            #add remaining data to list
            data_list.extend(await self._metric_convert(uom_list[panel],panel_data))

        output["metrics"] =data_list
        return output
