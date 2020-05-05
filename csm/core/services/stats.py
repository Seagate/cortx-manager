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
from eos.utils.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.errors import CsmInternalError

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
        output["metrics"] = panel_data["list"]
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
        Log.debug('Get panels requested: id=%s, panels=%s' %(stats_id, str(panels_list)))
        output = {}
        output["id"]=stats_id
        data_list = []
        for panel in panels_list:
            panel_data = await self._stats_provider.process_request(
                                                  stats_id = stats_id,
                                                  panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = "",
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = "",
                                                  output_format = output_format,
                                                  query = "")
            data_list.extend(panel_data["list"])
        output["metrics"] =data_list
        return output

    async def get_metrics(self, stats_id, metrics_list, from_t, to_t, interval,
                          total_sample, output_format) -> Dict:
        """
        Fetch statistics for selected panel.metric list (simplified - reduced parameter set)
        panels : { "<panel>": {"metric":[...], "unit":[...]}}
        """
        Log.debug("Get metrics requested: id=%s, interval=%s" %(str(stats_id), interval))
        output = {}
        panels = {}
        try:
            for metric in metrics_list:
                li = metric.split(".")
                if li[0] not in panels:
                    panels[li[0]] = {"metric": [li[1]], "unit":[]}
                else:
                    panels[li[0]]["metric"].append(li[1])
                if len(li) == 2:
                    panels[li[0]]["unit"].append("")
                else:
                    panels[li[0]]["unit"].append(li[2])
        except:
            raise CsmInternalError("Stats: Invalid metric list %s" %metrics_list)

        output["id"]=stats_id
        data_list = []
        for panel in panels.keys():
            Log.debug('metric[%s] = %s' %(str(panel), str(panels[panel]["metric"])))
            panel_data = await self._stats_provider.process_request(
                                                  stats_id = stats_id,
                                                  panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = panels[panel]["metric"],
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = panels[panel]["unit"],
                                                  output_format = output_format,
                                                  query = "")
            data_list.extend(panel_data["list"])
        output["metrics"] = data_list
        return output
