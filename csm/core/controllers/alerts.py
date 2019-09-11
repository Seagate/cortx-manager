#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          alerts.py
 Description:       Controllers for alerts

 Creation Date:     09/05/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from aiohttp import web
from csm.core.blogic.services.alerts import AlertsAppService


class AlertsListRestView(web.View):
    def __init__(self, request, alerts_service: AlertsAppService):
        super().__init__(request)
        self.alerts_service = alerts_service

    async def get(self):
        """Calling Alerts Get Method"""
        duration = self.request.rel_url.query.get("duration", None)
        offset = self.request.rel_url.query.get("offset", None)
        page_limit = self.request.rel_url.query.get("limit", None)
        sort_by = self.request.rel_url.query.get("sortby", "created_time")
        direction = self.request.rel_url.query.get("dir", "desc")

        if offset is not None:
            offset = int(offset)
        
        if page_limit is not None:
            page_limit = int(page_limit)

        return await self.alerts_service.fetch_all_alerts(
            duration, direction, sort_by, offset, page_limit)


class AlertsRestView(web.View):
    def __init__(self, request, alerts_service: AlertsAppService):
        super().__init__(request)
        self.alerts_service = alerts_service

    async def patch(self):
        """ Update Alert """
        alert_id = self.request.match_info["alert_id"]
        body = await self.request.json()
        return await self.alerts_service.update_alert(alert_id, body)


# AIOHTTP does not provide a way to pass custom parameters to its views.
# It is a workaround.
class AlertsRestController:
    def __init__(self, alerts_service: AlertsAppService):
        self.alerts_service = alerts_service

    def get_list_view_class(self):
        class Child(AlertsListRestView):
            def __init__(child_self, request):
                super().__init__(request, self.alerts_service)
        return Child

    def get_view_class(self):
        class Child(AlertsRestView):
            def __init__(child_self, request):
                super().__init__(request, self.alerts_service)
        return Child
