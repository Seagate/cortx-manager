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
# Last route is for debugging purposes only. Please see the description of the
# process_dbg_static_page() method.

from csm.core.views import *

def add_routes(self):
    # todo: Will be restructuring this part on Tuesday Morning.
    # self._app.router.add_view("/csm", CsmCliView),
    # self._app.web.get("/ws", self.process_websocket),
    self._app.router.add_view("/api/v1/alerts", Alerts),
    self._app.router.add_view("/api/v1/alerts/{alerts_id}", Alerts),
    # self._app.router.add_view('/{path:.*}', self.process_dbg_static_page)
