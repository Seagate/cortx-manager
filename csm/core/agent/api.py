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
import traceback
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
from csm.common.cluster import Cluster
from csm.common.errors import CsmError, CsmNotFoundError
from csm.core.routes import add_routes
from csm.core.blogic.services.alerts import AlertsAppService
from csm.core.controllers import AlertsRestController


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
            raise CsmError(errno.ENOENT,
                           'cluster config file %s does not exist' % inventory_file)

    @staticmethod
    def get_cluster():
        return CsmApi._cluster

    @staticmethod
    def set_cluster(cluster):
        CsmApi._cluster = cluster

    @staticmethod
    def process_request(command, request: Request, callback=None):
        """
        Processes requests received from client using a backend provider.
        Provider is loaded initially and instance is reused for future calls.
        """
        if CsmApi._cluster is None:
            raise CsmError(errno.ENOENT, 'CSM API not initialized')
        Log.info('command=%s action=%s args=%s' % (command,
                                                   request.action(),
                                                   request.args()))
        if not command in CsmApi._providers.keys():
            CsmApi._providers[command] = ProviderFactory.get_provider(command,
                                                                      CsmApi._cluster)
        provider = CsmApi._providers[command]
        return provider.process_request(request, callback)


class CsmRestApi(CsmApi, ABC):
    """ REST Interface to communicate with CSM """

    @staticmethod
    def init(alerts_service):
        CsmApi.init()
        CsmRestApi._queue = asyncio.Queue()
        CsmRestApi._bgtask = None
        CsmRestApi._wsclients = WeakSet()
        CsmRestApi._app = web.Application(
            middlewares=[CsmRestApi.rest_middleware]
        )

        alerts_ctrl = AlertsRestController(alerts_service)
        add_routes(CsmRestApi, alerts_ctrl)

        CsmRestApi._app.on_startup.append(CsmRestApi._on_startup)
        CsmRestApi._app.on_shutdown.append(CsmRestApi._on_shutdown)

    @staticmethod
    def error_response(err: Exception) -> dict:
        resp = {
            "message_id": None,
            "message": None,
            "error_format_args": {},  # Empty for now
            # TODO: Should we send trace only when we are in debug mode? 
            "stacktrace": traceback.format_exc().splitlines()
        }

        if isinstance(err, CsmError):
            resp["message_id"] = err.rc()
            resp["message"] = err.error()
        else:
            resp["message"] = str(err)

        return resp


    @staticmethod
    def json_serializer(*args, **kwargs):
        kwargs['default'] = str
        return json.dumps(*args, **kwargs)

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

            return web.json_response(resp_obj, status=200, 
                                     dumps=CsmRestApi.json_serializer)
        # todo: Changes for handling all Errors to be done.
        except CsmNotFoundError as e:
            return web.json_response(CsmRestApi.error_response(e), status=404)
        except CsmError as e:
            return web.json_response(CsmRestApi.error_response(e), status=400)
        except Exception as e:
            return web.json_response(CsmRestApi.error_response(e), status=422)

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
                    Log.debug('REST API websock msg (ignored): %s' % msg)
                elif msg.type == web.WSMsgType.ERROR:
                    Log.debug('REST API websock exception: %s' % ws.exception())
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
