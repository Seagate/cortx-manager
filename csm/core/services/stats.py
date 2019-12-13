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
        Fetch specific stat
        :return: :type:list
        """
        return await self._stats_provider.process_request(stats_id = stats_id, panel = panel,
                                                  from_t = from_t, duration_t = to_t,
                                                  metric_list = metric_list,
                                                  interval = interval,
                                                  total_sample = total_sample,
                                                  unit = unit.lower(),
                                                  output_format = output_format,
                                                  query = query)

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
        Fetch Panels list
        """
        panel_list_dict_keys = await self._stats_provider.get_panels()
        return {"panel_list": list(panel_list_dict_keys)}
