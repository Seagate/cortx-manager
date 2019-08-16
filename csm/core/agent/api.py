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
from csm.common.cluster import Cluster
from csm.common.errors import CsmError
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
    def process_request(command, request, callback=None):
        """
        Processes requests received from client using a backend provider.
        Provider is loaded initially and instance is reused for future calls.
        """

        if CsmApi._cluster == None:
            raise CsmError(errno.ENOENT, 'CSM API not initialized')
        Log.info('command=%s action=%s args=%s' %(command, \
            request.action(), request.args()))
        if not command in CsmApi._providers.keys():
            CsmApi._providers[command] = ProviderFactory.get_provider(command, CsmApi._cluster)
        provider = CsmApi._providers[command]
        return provider.process_request(request, callback)


class CsmRestApi(CsmApi, ABC):
    """ REST Interface to communicate with CSM """
    @staticmethod
    def init():
        CsmApi.init()
        CsmApi._app = web.Application()
        CsmApi._app.add_routes([
            web.get("/csm", CsmRestApi.process_request),
            web.get("/ws", CsmRestApi.process_websocket),
            web.get('/{path:.*}', CsmRestApi.process_dbg_static_page)
        ])
        CsmApi._app.on_startup.append(CsmRestApi._on_startup)
        CsmApi._app.on_shutdown.append(CsmRestApi._on_shutdown)

    @staticmethod
    def run(port):
        web.run_app(CsmApi._app, port=port, reuse_port=True)

    @staticmethod
    async def process_request(request):
        """ Receives a request, processes and sends response back to client """
        cmd = request.rel_url.query['cmd']
        action = request.rel_url.query['action']
        args = request.rel_url.query['args']

        request = Request(action, args)
        response = CsmApi.process_request(cmd, request)
        response_msg = {'status': response.rc(), 'message': response.output()}
        Log.debug('response_msg: %s' %response_msg)
        return web.Response(text=json.dumps(response_msg), status=200)

    @staticmethod
    async def process_websocket(request):
        """ Handles websocket connection """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        Log.debug('REST API websock connection opened')
        request.app['wsclients'].add(ws)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    Log.debug('REST API websock msg (ignored): %s' %msg)
                elif msg.type == web.WSMsgType.ERROR:
                    Log.debug('REST API websock exception: %s' %ws.exception())
            Log.debug('REST API websock connection closed')
        finally:
            request.app['wsclients'].discard(ws)
        return ws

    @staticmethod
    async def _on_startup(app):
        Log.debug(f'REST API startup')
        app['bgtask'] = app.loop.create_task(CsmRestApi._websock_bg(app))
        app['wsclients'] = WeakSet()

    @staticmethod
    async def _on_shutdown(app):
        Log.debug(f'REST API shutdown')
        app['bgtask'].cancel()

    @staticmethod
    async def _websock_bg(app):
        Log.debug(f'REST API websock background task started')
        try:
            while True:
                await asyncio.sleep(5)

                ts = datetime.utcnow().isoformat()
                alert = dict(id=None, status=0,
                    result=dict(type='alert', time=f'{ts}Z'))
                await CsmRestApi._websock_broadcast(app, json.dumps(alert))
        except asyncio.CancelledError:
            Log.debug(f'REST API websock background task canceled')

        Log.debug(f'REST API websock background task done')

    @staticmethod
    async def _websock_broadcast(app, msg):
        # do explicit copy because the list can change asynchronously
        clients = app['wsclients'].copy()
        try:
            for ws in clients:
                await ws.send_str(msg)
        except:
            Log.debug(f'REST API websock broadcast error')

    @staticmethod
    async def process_dbg_static_page(request):
        base = "src/core/agent/dbgwbi"
        path = request.match_info.get('path', '.')
        realpath = os.path.abspath(f'{base}/{path}')
        if os.path.exists(realpath) and os.path.isdir(realpath):
            realpath = os.path.abspath(f'{realpath}/index.html')
        if os.path.exists(realpath):
            return web.FileResponse(realpath)
        return web.FileResponse(f'{base}/error.html')
