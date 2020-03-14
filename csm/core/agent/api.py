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
import ssl
from concurrent.futures import CancelledError as ConcurrentCancelledError
from asyncio import CancelledError as AsyncioCancelledError
from weakref import WeakSet
from aiohttp import web, web_exceptions
from abc import ABC
from secure import SecureHeaders
from csm.core.providers.provider_factory import ProviderFactory
from csm.core.providers.providers import Request, Response
from csm.common.observer import Observable
from csm.common.payload import *
from csm.common.conf import Conf, ConfSection, DebugConf
from csm.common.log import Log
from csm.common.services import Service
from csm.core.blogic import const
from csm.common.cluster import Cluster
from csm.common.errors import (CsmError, CsmNotFoundError, CsmPermissionDenied,
                               CsmInternalError, ResourceExist)
from csm.core.routes import ApiRoutes
from csm.core.services.alerts import AlertsAppService
from csm.core.services.usl import UslService
from csm.core.services.file_transfer import DownloadFileEntity
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.core.controllers import UslController
from csm.core.controllers import CsmRoutes


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
    def init(alerts_service, usl_service):
        CsmApi.init()
        CsmRestApi._queue = asyncio.Queue()
        CsmRestApi._bgtask = None
        CsmRestApi._wsclients = WeakSet()

        CsmRestApi._app = web.Application(
            middlewares=[CsmRestApi.set_secure_headers,
                         CsmRestApi.rest_middleware,
                         CsmRestApi.session_middleware,
                         CsmRestApi.permission_middleware]
        )

        usl_ctrl = UslController(usl_service)
        CsmRoutes.add_routes(CsmRestApi._app)
        ApiRoutes.add_rest_api_routes(CsmRestApi._app.router, usl_ctrl)
        ApiRoutes.add_websocket_routes(
            CsmRestApi._app.router, CsmRestApi.process_websocket)

        CsmRestApi._app.on_startup.append(CsmRestApi._on_startup)
        CsmRestApi._app.on_shutdown.append(CsmRestApi._on_shutdown)

    @staticmethod
    def is_debug(request) -> bool:
        return 'debug' in request.rel_url.query

    @staticmethod
    def error_response(err: Exception, request) -> dict:
        resp = {
            "error_code": None,
            "message_id": None,
            "message": None,
            "error_format_args": {},  # Empty for now
        }

        if CsmRestApi.is_debug(request):
            resp["stacktrace"] = traceback.format_exc().splitlines()

        if isinstance(err, CsmError):
            resp["error_code"] = err.rc()
            resp["message_id"] = err.message_id()
            resp["message"] = err.error()
            resp["error_format_args"] = err.message_args()
        elif isinstance(err, web_exceptions.HTTPError):
            resp["message"] = str(err)
            resp["error_code"] = err.status
        else:
            resp["message"] = str(err)
        if hasattr(request.session, "credentials"):
            Log.audit(f'User: {request.session.credentials.user_id} '
                  f'Request: {request} RC: {resp["error_code"]}' )
        else:
            Log.audit(f'Request: {request} RC: {resp["error_code"]}')
        return resp

    @staticmethod
    def json_serializer(*args, **kwargs):
        kwargs['default'] = str
        return json.dumps(*args, **kwargs)

    @staticmethod
    def json_response(resp_obj, status=200):
        return web.json_response(
            resp_obj, status=status, dumps=CsmRestApi.json_serializer)

    @classmethod
    def _unauthorised(cls, reason):
        Log.debug(f'Unautorized: {reason}')
        raise web.HTTPUnauthorized(headers=CsmAuth.UNAUTH)

    @staticmethod
    async def http_request_to_log_string(request):
        remote_ip = request.remote
        url = request.path
        method = request.method
        body = {}
        query = ()
        ct = request.headers.get('Content-Type')
        is_mulitpart = ct is not None and 'multipart' in ct
        if is_mulitpart:
            Log.info(f"request:{request} is_mulitpart:{is_mulitpart}"
                     f" content_length:{request.content_length}")
        if request.has_body and not is_mulitpart:
            query = request.query.items()
            body = await request.json()
        if body and isinstance(body, dict):
            for key in body.keys():
                if "password" in key:
                    body[key] = '*****'
        return (f"Remote_IP:{remote_ip} Url:{url} Method:{method} Query:{query}"
                f" Body:{body}")

    @staticmethod
    async def _resolve_handler(request):
        match_info = await request.app.router.resolve(request)
        return match_info.handler

    @classmethod
    async def _is_public(cls, request):
        handler = await cls._resolve_handler(request)
        return CsmView.is_public(handler, request.method)

    @classmethod
    async def _get_permissions(cls, request):
        handler = await cls._resolve_handler(request)
        return CsmView.get_permissions(handler, request.method)

    @classmethod
    @web.middleware
    async def session_middleware(cls, request, handler):
        log_message = await cls.http_request_to_log_string(request)
        Log.audit(log_message)
        session = None
        is_public = await cls._is_public(request)
        if not is_public:
            hdr = request.headers.get(CsmAuth.HDR)
            if not hdr:
                cls._unauthorised(f'No {CsmAuth.HDR} header')
            auth_type, session_id = hdr.split(' ')
            if auth_type != CsmAuth.TYPE:
                cls._unauthorised(f'Invalid auth type {auth_type}')
            Log.debug(f'Non-Public: {request}')
            try:
                session = await request.app.login_service.auth_session(session_id)
                Log.info(f'Username: {session.credentials.user_id}')
            except CsmError as e:
                cls._unauthorised(e.error())
            if not session:
                cls._unauthorised('Invalid auth token')
        else:
            Log.debug(f'Public: {request}')
        request.session = session
        return await handler(request)

    @classmethod
    @web.middleware
    async def permission_middleware(cls, request, handler):
        if request.session is not None:
            # Check user permissions
            required = await cls._get_permissions(request)
            verdict = (request.session.permissions & required) == required
            Log.debug(f'Required permissions: {required}')
            Log.debug(f'User permissions: {request.session.permissions}')
            Log.debug(f'Allow access: {verdict}')
            if not verdict:
                raise web.HTTPForbidden()
        return await handler(request)

    @staticmethod
    @web.middleware
    async def set_secure_headers(request, handler):
        resp = await handler(request)
        SecureHeaders(csp=True).aiohttp(resp)
        return resp

    @staticmethod
    @web.middleware
    async def rest_middleware(request, handler):
        try:
            resp = await handler(request)

            if isinstance(resp, DownloadFileEntity):
                file_resp = web.FileResponse(resp.path_to_file)
                file_resp.headers['Content-Disposition'] = f'attachment; filename="{resp.filename}"'
                return file_resp

            if isinstance(resp, web.StreamResponse):
                return resp

            status = 200
            if isinstance(resp, Response):
                resp_obj = {'message': resp.output()}
                status = resp.rc()
                if not 200 <= status <= 299:
                    Log.error(f"Error: ({status}):{resp_obj['message']}")
            else:
                resp_obj = resp
            Log.audit(f'User: {request.session.credentials.user_id} '
                      f'Request: {request} RC: {status}')
            return CsmRestApi.json_response(resp_obj, status)
        # todo: Changes for handling all Errors to be done.
        
        # These exceptions are thrown by aiohttp when request is cancelled
        # by client to complete task which are await use atomic
        except (ConcurrentCancelledError, AsyncioCancelledError) as e:
            log_message = await CsmRestApi.http_request_to_log_string(request)
            Log.warn(f"Client cancelled call for {log_message}")
            return CsmRestApi.json_response("Call cancelled by client", status=499)
        except web.HTTPException as e:
            Log.error(f'HTTP Exception {e.status}: {e.reason}')
            raise e
        except CsmNotFoundError as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request), status=404)
        except CsmPermissionDenied as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request), status=403)
        except ResourceExist  as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request),
                                            status=const.STATUS_CONFLICT)
        except CsmInternalError as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request), status=500)
        except CsmError as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request), status=400)
        except KeyError as e:
            Log.error(f"Error: {e} \n {traceback.format_exc()}")
            message = f"Missing Key for {e}"
            return CsmRestApi.json_response(CsmRestApi.error_response(KeyError(message), request), status=422)
        except Exception as e:
            Log.critical(f"Unhandled Exception Caught: {e} \n {traceback.format_exc()}")
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request), status=500)

    @staticmethod
    def run(port: int, https_conf: ConfSection, debug_conf: DebugConf):
        if not debug_conf.http_enabled:
            port = https_conf.port
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            if not all(map(os.path.exists,
                           (https_conf.certificate_path,
                            https_conf.private_key_path))):
                raise CsmError(errno.ENOENT, "Invalid path to certificate/private key")
            ssl_context.load_cert_chain(https_conf.certificate_path, https_conf.private_key_path)
        else:
            ssl_context = None

        web.run_app(CsmRestApi._app, port=port, ssl_context=ssl_context, 
                    access_log=Log.logger, access_log_format=const.REST_ACCESS_FORMAT)

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
    @CsmAuth.public
    async def process_websocket(request):
        """
        The method handles websocket connection.

        TODO: Implement authentication mechanism for websockets.
        As JavaScript WebSocket API does not support sending
        any custom headers during HTTP handshake stage, the
        'Authorization' header can not be used for websocket
        connection authentication. Some other authentication
        scheme should be designed for this case.
        For the time being the handler is marked as 'public'
        to disable authentication for websockets completely.
        """
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
        except AsyncioCancelledError:
            Log.debug('REST API websock background task canceled')

        Log.debug('REST API websock background task done')

    @staticmethod
    async def _websock_broadcast(msg):
        # do explicit copy because the list can change asynchronously
        clients = CsmRestApi._wsclients.copy()
        try:
            for ws in clients:
                json_msg = CsmRestApi.json_serializer(msg)
                await ws.send_str(json_msg)
        except:
            Log.debug('REST API websock broadcast error')

    @staticmethod
    async def _async_push(msg):
        return await CsmRestApi._queue.put(msg)

    @staticmethod
    def push(alert):
        coro = CsmRestApi._async_push(alert)
        asyncio.run_coroutine_threadsafe(coro, CsmRestApi._app.loop)
        return True


class AlertHttpNotifyService(Service):
    def __init__(self):
        super().__init__()
        self.unpublished_alerts = set()

    def push_unpublished(self):
        while self.unpublished_alerts:
            self.handle_alert()

    def handle_alert(self, alert):
        self.unpublished_alerts.add(alert)
        if CsmRestApi.push(alert):
            self.unpublished_alerts.discard(alert)
