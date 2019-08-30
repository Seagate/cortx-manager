#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          api_client.py
 Description:       Infrastructure for invoking business logic locally or
                    remotely or various available channels like REST.

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from aiohttp import web
from csm.core.controller.alerts import AlertsRestController
from csm.core.blogic.alerts.alerts import SyncAlertStorage, Alert, AlertsService
from csm.core.blogic.storage import SyncInMemoryKeyValueStorage


# TODO: Services and storages should not be instantiated by each controller
# separately.
storage = SyncAlertStorage(SyncInMemoryKeyValueStorage())
storage.store(Alert({'A':"b"}))
a = AlertsService(storage)
alerts = AlertsRestController(a)

class AlertsView(web.View):
    async def get(self):
        """Calling Alerts Get Method"""
        duration = self.request.rel_url.query.get("duration")
        offset = self.request.rel_url.query.get("offset", "")
        page_limit = self.request.rel_url.query.get("limit", "")
        sort_by = self.request.rel_url.query.get("sortby", "created_time")
        direction = self.request.rel_url.query.get("dir", "desc")
        return await alerts.fetch_all_alerts(duration, direction, sort_by,
                                                  offset,
                                                  page_limit)

    async def patch(self):
        """ Update Alert """
        alert_id = self.request.match_info["alert_id"]
        body = await self.request.json()
        return await alerts.update_alert(alert_id, body)
