#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          routes.py
 Description:       A file for AIOHTTP routes

 Creation Date:     09/05/2019
 Author:            Prathamesh Rodi
                    Alexander Nogikh

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

import os
from aiohttp import web
from csm.core.controllers import *


class ApiRoutes:
    @staticmethod
    def add_rest_api_routes(router, alerts_ctrl, stats_ctrl):
        # todo: Will be restructuring this part on Tuesday Morning.
        # self._app.router.add_view("/csm", CsmCliView),
        # self._app.web.get("/ws", self.process_websocket),
        router.add_view("/api/v1/alerts", alerts_ctrl.get_list_view_class()),
        router.add_view("/api/v1/alerts/{alert_id}", alerts_ctrl.get_view_class()),
        router.add_view("/api/v1/stats/{panel}", stats_ctrl.get_view_class()),
        # self._app.router.add_view('/{path:.*}', self.process_dbg_static_page)

    @staticmethod
    def add_websocket_routes(router, ws_handler):
        router.add_get("/ws", ws_handler)

    @staticmethod
    async def _process_dbg_static_page(request):
        """
        Static page handler is for debugging purposes only. To be
        deleted later when we have tests for aiohttp web sockets.
        HTML and JS debug files are loaded from 'dbgwbi' directory
        (which will be deleted later completely too).
        """
        base = "src/core/agent/dbgwbi"
        path = request.match_info.get('path', '.')
        realpath = os.path.abspath(f'{base}/{path}')
        if os.path.exists(realpath) and os.path.isdir(realpath):
            realpath = os.path.abspath(f'{realpath}/index.html')
        if os.path.exists(realpath):
            return web.FileResponse(realpath)
        return web.FileResponse(f'{base}/error.html')

    @staticmethod
    def add_debug_routes(router):
        router.add_view('/{path:.*}', ApiRoutes._process_dbg_static_page)
