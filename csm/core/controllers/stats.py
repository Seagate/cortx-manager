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
from aiohttp import web
from csm.core.services.stats import StatsAppService
import pdb

class StatsView(web.View):
    def __init__(self, request, stats_service: StatsAppService):
        super().__init__(request)
        self.stats_service = stats_service

    """
    GET REST implementation for Statistics request
    """
    async def get(self):
        """Calling Stats Get Method"""
        stats_id = self.request.rel_url.query.get("id", None)
        panel = self.request.match_info["panel"]
        from_t = self.request.rel_url.query.get("from", None)
        to_t = self.request.rel_url.query.get("to", None)
        metric_list = self.request.rel_url.query.getall("metric_list", None)
        interval = self.request.rel_url.query.get("interval", None)
        output_format = self.request.rel_url.query.get("output_format", "gui")
        query = self.request.rel_url.query.get("query", None)

        return await self.stats_service.get(stats_id, panel, from_t, to_t, metric_list,
                                            interval, output_format, query)


# AIOHTTP does not provide a way to pass custom parameters to its views.
# It is a workaround.
class StatsHttpController:
    def __init__(self, stats_service: StatsAppService):
        self.stats_service = stats_service

    def get_view_class(self):
        class Child(StatsView):
            def __init__(child_self, request):
                super().__init__(request, self.stats_service)
        return Child
