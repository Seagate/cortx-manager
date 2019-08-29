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

import os
import errno
import yaml
import asyncio
import json
from weakref import WeakSet
from datetime import datetime
from aiohttp import web
from abc import ABC

from csm.core.providers.provider_factory import ProviderFactory
from csm.core.providers.providers import Request, Response
from csm.common.payload import *
from csm.common.conf import Conf
from csm.common.log import Log
from csm.core.blogic import const
from csm.core.blogic.alerts.alerts import AlertsService
from csm.common.cluster import Cluster
from csm.common.errors import CsmError, CsmNotFoundError
from csm.common.ha_framework import PcsHAFramework
from csm.core.blogic.csm_ha import CsmResourceAgent

class CsmApi(ABC):
    """ Interface class to communicate with RAS API """
    _providers = {}
    _cluster = None

    @staticmethod
    def init():
        """ API server initialization. Validates and Loads configuration """

        # Validate configuration files are present
        inventory_file = const.INVENTORY_FILE
        if not os.path.isfile(inventory_file):
            raise CsmError(errno.ENOENT, 'cluster config file %s does not exist' %inventory_file)

        # Instantiation of cluster
        _csm_resources = Conf.get(const.CSM_GLOBAL_INDEX, "HA.resources")
        _csm_ra = {
            "csm_resource_agent": CsmResourceAgent(_csm_resources)
        }
        _ha_framework = PcsHAFramework(_csm_ra)
        CsmApi._cluster = Cluster(inventory_file, _ha_framework)

    @staticmethod
    def get_cluster():
        return CsmApi._cluster

    @staticmethod
    def process_request(command, request: Request, callback=None):
        """
        Processes requests received from client using a backend provider.
        Provider is loaded initially and instance is reused for future calls.
        """
        if CsmApi._cluster is None:
            raise CsmError(errno.ENOENT, 'CSM API not initialized')
        Log.info('command=%s action=%s args=%s' %(command, \
            request.action(), request.args()))
        if not command in CsmApi._providers.keys():
            CsmApi._providers[command] = ProviderFactory.get_provider(command, CsmApi._cluster)
        provider = CsmApi._providers[command]
        return provider.process_request(request, callback)

# Let it all reside in a separate controller until we've all ageed on
# request processing architecture
class AlertsRestController:
    def __init__(self, service: AlertsService):
        self.service = service

    # This function allows to call synchronous code in a separate thread and 
    # then await it. It won't be needed if all code uses asyncio
    async def _call_nonasync(self, function, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, function, *args)

    async def update_alert(self, request):
        alert_id = request.match_info["alert_id"]
        body = await request.json()
        result = await self._call_nonasync(
            self.service.update_alert, alert_id, body)
        return result.data()

    # This method is for debugging purposes only
    async def fetch_alert(self, request):
        alert_id = request.match_info["alert_id"]
        alert = await self._call_nonasync(self.service.fetch_alert, alert_id)
        if not alert:
            raise CsmNotFoundError("Alert is not found")
        return alert.data()


class CsmRestApi(CsmApi, ABC):
    """ REST Interface to communicate with CSM """
    @staticmethod
    def init(alerts_service: AlertsService):
        CsmApi.init()
        CsmRestApi._queue = asyncio.Queue()
        CsmRestApi._bgtask = None
        CsmRestApi._wsclients = WeakSet()
        CsmRestApi._app = web.Application(
            middlewares=[CsmRestApi.rest_middleware]
        )

        alerts = AlertsRestController(alerts_service)

        # Last route is for debugging purposes only. Please see
        # the description of the process_dbg_static_page() method.
        CsmRestApi._app.add_routes([
            web.get("/csm", CsmRestApi.process_request),
            web.get("/ws", CsmRestApi.process_websocket),
            web.get("/api/alerts/{alert_id}", alerts.fetch_alert),
            web.patch("/api/alerts/{alert_id}", alerts.update_alert),
            web.get('/{path:.*}', CsmRestApi.process_dbg_static_page)
        ])
        CsmRestApi._app.on_startup.append(CsmRestApi._on_startup)
        CsmRestApi._app.on_shutdown.append(CsmRestApi._on_shutdown)

    @staticmethod
    @web.middleware
    async def rest_middleware(request, handler):
        try:
            resp = await handler(request)
            if isinstance(resp, web.FileResponse):
                return resp
            
            if isinstance(resp, Response):
                resp_obj = {'status': resp.rc(), 'message': resp.output()}
            else:
                resp_obj = resp

            return web.json_response(resp_obj, status=200)
        except CsmNotFoundError as e:
            return web.json_response({'message': e.error()}, status=404)
        except CsmError as e:
            return web.json_response({'message': e.error()}, status=400)
    @staticmethod
    def run(port):
        web.run_app(CsmRestApi._app, port=port)

    @staticmethod
    async def process_request(request):
        """ Receives a request, processes and sends response back to client """
        cmd = request.rel_url.query['cmd']
        action = request.rel_url.query['action']
        args = request.rel_url.query['args']

        request = Request(action, args)
        response = CsmApi.process_request(cmd, request)

        return response

    @staticmethod
    async def process_websocket(request):
        """ Handles websocket connection """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        Log.debug('REST API websock connection opened')
        CsmRestApi._wsclients.add(ws)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    Log.debug('REST API websock msg (ignored): %s' %msg)
                elif msg.type == web.WSMsgType.ERROR:
                    Log.debug('REST API websock exception: %s' %ws.exception())
            Log.debug('REST API websock connection closed')
            await ws.close()
        finally:
            CsmRestApi._wsclients.discard(ws)
        return ws

    @staticmethod
    async def _on_startup(app):
        Log.debug('REST API startup')
        CsmRestApi._bgtask = app.loop.create_task(CsmRestApi._websock_bg())

    @staticmethod
    async def _on_shutdown(app):
        Log.debug('REST API shutdown')
        CsmRestApi._bgtask.cancel()

    @staticmethod
    async def _websock_bg():
        Log.debug('REST API websock background task started')
        try:
            while True:
                msg = await CsmRestApi._queue.get()
                await CsmRestApi._websock_broadcast(msg)
        except asyncio.CancelledError:
            Log.debug('REST API websock background task canceled')

        Log.debug('REST API websock background task done')

    @staticmethod
    async def _websock_broadcast(msg):
        # do explicit copy because the list can change asynchronously
        clients = CsmRestApi._wsclients.copy()
        try:
            for ws in clients:
                await ws.send_str(json.dumps(msg))
        except:
            Log.debug('REST API websock broadcast error')

    @staticmethod
    async def process_dbg_static_page(request):
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
    async def _async_push(msg):
        return await CsmRestApi._queue.put(msg)

    @staticmethod
    def push(alert):
        coro = CsmRestApi._async_push(alert)
        asyncio.run_coroutine_threadsafe(coro, CsmRestApi._app.loop)
        return True
