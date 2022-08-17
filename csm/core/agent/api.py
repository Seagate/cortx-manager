# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import os
import errno
import asyncio
import json
import traceback
import signal
import ssl
import time
from concurrent.futures import (CancelledError as ConcurrentCancelledError,
                                TimeoutError as ConcurrentTimeoutError)
from asyncio import CancelledError as AsyncioCancelledError
from weakref import WeakSet
from aiohttp import web, web_exceptions
from aiohttp.client_exceptions import ServerDisconnectedError, ClientConnectorError, ClientOSError
from abc import ABC
from aiohttp.web_middlewares import normalize_path_middleware
from secure import SecureHeaders
from typing import Dict, Tuple
from csm.core.providers.provider_factory import ProviderFactory
from csm.core.providers.providers import Request, Response
from csm.core.services.sessions import LoginService
from cortx.utils.conf_store.conf_store import Conf
from csm.common.conf import ConfSection, DebugConf
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.errors import (CsmError, CsmNotFoundError, CsmPermissionDenied,
                               CsmInternalError, InvalidRequest, ResourceExist,
                               CsmNotImplemented, CsmServiceConflict, CsmGatewayTimeout,
                               CsmRequestCancelled, CsmUnauthorizedError, CSM_UNKNOWN_ERROR,
                               CSM_HTTP_ERROR)
from csm.core.routes import ApiRoutes
from csm.core.services.file_transfer import DownloadFileEntity
from csm.core.controllers.view import CsmView, CsmAuth, CsmHttpException
from csm.core.controllers.routes import CsmRoutes
from cortx.utils.errors import DataAccessError
from marshmallow import ValidationError, fields
from csm.core.controllers.validators import ValidateSchema


class CsmApi(ABC):
    """Interface class to communicate with RAS API."""

    _providers = {}
    _cluster = None

    @staticmethod
    def init():
        """Initialize API server, validate and load configuration."""
        pass

    @staticmethod
    def get_cluster():
        return CsmApi._cluster

    @staticmethod
    def set_cluster(cluster):
        CsmApi._cluster = cluster

    @staticmethod
    def process_request(command, request: Request, callback=None):
        """
        Process requests received from client using a backend provider.

        Provider is loaded initially and instance is reused for future calls.
        """
        if CsmApi._cluster is None:
            raise CsmError(errno.ENOENT, 'CSM API not initialized')
        Log.info('command=%s action=%s args=%s' % (command,
                                                   request.action(),
                                                   request.args()))
        if command not in CsmApi._providers:
            CsmApi._providers[command] = ProviderFactory.get_provider(command,
                                                                      CsmApi._cluster)
        provider = CsmApi._providers[command]
        return provider.process_request(request, callback)

class ErrorResponseSchema(ValidateSchema):
    """
    Error Response validation schema
    """
    error_code = fields.Int(data_key=const.ERROR_CODE, required=True)
    message_id = fields.Str(data_key=const.MESSAGE_ID, required=True)
    message = fields.Str(data_key=const.MESSAGE_LITERAL, required=True)


class CsmRestApi(CsmApi, ABC):
    """REST Interface to communicate with CSM."""
    # __unsupported_features = None
    __is_shutting_down = False
    __nreq = 0
    __nblocked = 0
    __request_quota = 0

    @staticmethod
    def init():
        CsmApi.init()
        CsmRestApi._queue = asyncio.Queue()
        CsmRestApi._bgtasks = []
        CsmRestApi._wsclients = WeakSet()

        CsmRestApi.__request_quota = int(Conf.get(const.CSM_GLOBAL_INDEX, const.AGENT_REQUEST_QUOTA))
        Log.info(f"CSM request quota is set to {CsmRestApi.__request_quota}")

        CsmRestApi._app = web.Application(
            middlewares=[CsmRestApi.throttler_middleware,
                         CsmRestApi.set_secure_headers,
                         CsmRestApi.rest_middleware,
                         CsmRestApi.session_middleware,
                         CsmRestApi.permission_middleware,
                         web.normalize_path_middleware(remove_slash=True, append_slash = False)]
        )
        CsmRestApi._app.url_map.strict_slashes = False
        CsmRoutes.add_routes(CsmRestApi._app)
        ApiRoutes.add_websocket_routes(
            CsmRestApi._app.router, CsmRestApi.process_websocket)
        ApiRoutes.add_swagger_ui_routes(CsmRestApi._app.router)

        CsmRestApi._app.on_response_prepare.append(CsmRestApi._hide_headers)
        CsmRestApi._app.on_startup.append(CsmRestApi._on_startup)
        CsmRestApi._app.on_shutdown.append(CsmRestApi._on_shutdown)

    @staticmethod
    def is_debug(request) -> bool:
        return 'debug' in request.rel_url.query

    @staticmethod
    def error_response(err: Exception, **kwargs) -> dict:
        resp = {
            "error_code": None,
            "message": None,
            "message_id": None
        }

        request = kwargs.get("request")
        if CsmRestApi.is_debug(request):
            resp["stacktrace"] = traceback.format_exc().splitlines()

        if isinstance(err, CsmError):
            resp["error_code"] = int(err.rc())
            resp["message"] = err.error()
            resp["message_id"] = err.message_id()
            message_args = err.message_args()
            if message_args is not None:
                resp["error_format_args"] = err.message_args()
        elif isinstance(err, web_exceptions.HTTPError):
            resp["error_code"] = CSM_HTTP_ERROR
            resp["message_id"] = const.HTTP_ERROR
            resp["message"] = str(err.reason)
        else:
            resp["message"] = f'{str(err)}'
            resp["message_id"] = const.UNKNOWN_ERROR
            resp["error_code"] = CSM_UNKNOWN_ERROR

        try:
            # CSM error response should have error_code message and message_id
            # Here we only check the Error response format
            # For incorrect format, only log the error
            schema = ErrorResponseSchema()
            err_response = schema.load(resp, unknown='EXCLUDE')
        except ValidationError as val_err:
            Log.error(f"Malformed error response format: {val_err}")

        return err_response

    @staticmethod
    def json_serializer(*args, **kwargs):
        kwargs['default'] = str
        return json.dumps(*args, **kwargs)

    @staticmethod
    def json_response(resp_obj, status=200):
        return web.json_response(
            resp_obj, status=status, dumps=CsmRestApi.json_serializer)

    @staticmethod
    def _unauthorised(reason: str):
        Log.debug(f'Unautorized: {reason}')
        raise CsmUnauthorizedError(
            desc="Invalid authentication credentials for the target resource.")

    @staticmethod
    async def _resolve_handler(request):
        match_info = await request.app.router.resolve(request)
        return match_info.handler

    @staticmethod
    async def _is_public(request):
        path = request.url.path
        if path.startswith(const.SWAGGER_UI_URL) or path.startswith(const.SWAGGER_UI_STATICS_URL):
            return True
        handler = await CsmRestApi._resolve_handler(request)
        return CsmView.is_public(handler, request.method)

    @staticmethod
    async def _is_hybrid(request):
        handler = await CsmRestApi._resolve_handler(request)
        return CsmView.is_hybrid(handler, request.method)

    @classmethod
    async def _get_permissions(cls, request):
        handler = await CsmRestApi._resolve_handler(request)
        return CsmView.get_permissions(handler, request.method)

    # @classmethod
    # async def get_unsupported_features(cls):
    #     if cls.__unsupported_features is None:
    #         db = unsupported_features.UnsupportedFeaturesDB()
    #         cls.__unsupported_features = await db.get_unsupported_features()
    #     return cls.__unsupported_features

    # @classmethod
    # async def is_feature_supported(cls, component, feature):
    #     unsupported_features = await cls.get_unsupported_features()
    #     for entry in unsupported_features:
    #         if (
    #             component == entry[const.COMPONENT_NAME] and
    #             feature == entry[const.FEATURE_NAME]
    #         ):
    #             return False
    #     return True

    # @classmethod
    # async def check_for_unsupported_endpoint(cls, request):
    #     """Check whether the endpoint is supported. If not, send proper error reponse."""
    #     def getMatchingEndpoint(endpoint_map, path):
    #         for key, value in endpoint_map.items():
    #             map_re = f'^{key}$'.replace("*", r"[\w\d]*")
    #             if re.search(rf"{map_re}", path):
    #                 return value

    #     feature_endpoint_map = Json(const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
    #     endpoint = getMatchingEndpoint(feature_endpoint_map, request.path)
    #     if endpoint:
    #         if endpoint[const.DEPENDENT_ON]:
    #             for component in endpoint[const.DEPENDENT_ON]:
    #                 if not await cls.is_feature_supported(component, endpoint[const.FEATURE_NAME]):
    #                     Log.debug(f"The request {request.path} "
    #                               f"of feature {endpoint[const.FEATURE_NAME]} "
    #                               f"is not supported by {component}")
    #                     raise InvalidRequest("This feature is not supported on this environment.")
    #         if not await cls.is_feature_supported(const.CSM_COMPONENT_NAME,
    #                                               endpoint[const.FEATURE_NAME]):
    #             Log.debug(f"The request {request.path} "
    #                       f"of feature {endpoint[const.FEATURE_NAME]} "
    #                       f"is not supported by {const.CSM_COMPONENT_NAME}")
    #             raise InvalidRequest("This feature is not supported on this environment.")
    #     else:
    #         Log.debug(f"Feature endpoint is not found for {request.path}")

    @staticmethod
    def _extract_bearer(headers: Dict) -> Tuple[str, str]:
        """
        Extract the bearer token from HTTP headers.

        :param headers: HTTP headers.
        :returns: bearer token.
        """
        hdr = headers.get(CsmAuth.HDR)
        if not hdr:
            raise CsmNotFoundError(f'No {CsmAuth.HDR} header')
        auth_pair = hdr.split(' ')
        if len(auth_pair) != 2:
            raise CsmNotFoundError(f'The header is incorrect. Expected "{CsmAuth.HDR} session_id"')
        auth_type, session_id = auth_pair
        if auth_type != CsmAuth.TYPE:
            raise CsmNotFoundError(f'Invalid auth type {auth_type}')
        return session_id

    @staticmethod
    async def _validate_bearer(login_service: LoginService, session_id: str):
        """
        Validate the bearer token.

        Search for the session with ID equal to the token value and return it.
        Throw a Permission denied exception otherwise.
        :param login_service: login service.
        :param auth_type: authorization token type.
        :param session_id: bearer token's value.
        :returns: session object.
        """
        try:
            session = await login_service.auth_session(session_id)
        except CsmError as e:
            raise CsmNotFoundError(e.error())
        if not session:
            raise CsmNotFoundError('Invalid auth token')
        return session

    @staticmethod
    def _retrieve_config(request):
        path = request.path
        method = request.method
        key = method + ":" + path
        conf_key = CsmAuth.HYBRID_APIS[key]
        return Conf.get(const.CSM_GLOBAL_INDEX, conf_key)

    @staticmethod
    @web.middleware
    async def throttler_middleware(request, handler):
        if CsmRestApi.__nreq >= CsmRestApi.__request_quota:
            # This block get executed when number of request reaches the request quota
            CsmRestApi.__nblocked += 1
            msg = (f"The request is blocked because the number of requests reached threshold\n"
                   f"Number of requests blocked since the start is {CsmRestApi.__nblocked}")
            Log.warn(msg)
            return web.Response(status=429, text="Too many requests")
        else:
            # This block get executed when number of request are less than request quota
            # Increment the counter for number of request executing
            CsmRestApi.__nreq += 1

        try:
            # Here we call handler
            # Handler can return json response or can raise an exception
            res = await handler(request)
        finally:
            # Decrements the counter of number of request executing
            # This block always gets executed
            CsmRestApi.__nreq -= 1
        return res

    @staticmethod
    @web.middleware
    async def session_middleware(request, handler):
        session = None
        is_public = await CsmRestApi._is_public(request)
        is_hybrid = await CsmRestApi._is_hybrid(request)
        if is_hybrid:
            is_public = True
            conf_key = CsmRestApi._retrieve_config(request)
            if conf_key.lower() == const.ENABLE:
                is_public = False
        Log.debug(f'{"Public" if is_public else "Non-public"}: {request}')
        try:
            if not is_public:
                session_id = CsmRestApi._extract_bearer(request.headers)
                session = await CsmRestApi._validate_bearer(
                    request.app.login_service, session_id)
                Log.info("Session token validated. User:"\
                    f" {session.credentials.user_id}")
        except CsmNotFoundError as e:
            CsmRestApi._unauthorised(e.error())
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
                Log.info(f"Authorization failed. User:"\
                f" {request.session.credentials.user_id}")
                raise CsmPermissionDenied("Access to the requested resource"\
                    " is forbidden")
            Log.info(f"Authorization successful. User:"\
                f" {request.session.credentials.user_id}")
        return await handler(request)

    @staticmethod
    @web.middleware
    async def set_secure_headers(request, handler):
        resp = await handler(request)
        SecureHeaders(csp=True, server=True).aiohttp(resp)
        return resp

    @staticmethod
    @web.middleware
    async def rest_middleware(request, handler):
        if CsmRestApi.__is_shutting_down:
            return CsmRestApi.json_response("CSM agent is shutting down", status=503)
        request.request_id = int(time.time())
        try:
            request_body = dict(request.rel_url.query) if request.rel_url.query else {}
            if not request_body and request.content_length and request.content_length > 0:
                try:
                    request_body = await request.json()
                except Exception:
                    request_body = {}
                if request_body:
                    for key in list(request_body.keys()):
                        lower_key = key.lower()
                        if (lower_key.find("password") > -1 or lower_key.find("passwd") > -1 or
                                lower_key.find("secret") > -1):
                            del(request_body[key])
            # Disabled: unsupported features endpoint checking
            # try:
            #     await CsmRestApi.check_for_unsupported_endpoint(request)
            # except DataAccessError as e:
            #     Log.warn(f"Exception: {e}")
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
            return CsmRestApi.json_response(resp_obj, status)
        # todo: Changes for handling all Errors to be done.

        # These exceptions are thrown by aiohttp when request is cancelled
        # by client to complete task which are await use atomic
        except (ConcurrentCancelledError, AsyncioCancelledError):
            Log.warn(f"Client cancelled call for {request.method} {request.path}")
            resp = CsmRestApi.error_response(
                    CsmRequestCancelled(desc="Call cancelled by client"),
                    request=request, request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=499)
        except CsmHttpException as e:
            raise e
        except web.HTTPException as e:
            Log.error(f'HTTP Exception {e.status}: {e.reason}')
            resp = CsmRestApi.error_response(e, request=request,
                    request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=e.status)
        except DataAccessError as e:
            Log.error(f"Failed to access the database: {e}")
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=503)
        except InvalidRequest as e:
            Log.debug(f"Invalid Request: {e} \n {traceback.format_exc()}")
            resp = CsmRestApi.error_response(e, request=request,
                    request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=400)
        except CsmNotFoundError as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=404)
        except CsmPermissionDenied as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=403)
        except ResourceExist as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=const.STATUS_CONFLICT)
        except CsmInternalError as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=500)
        except CsmNotImplemented as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=501)
        except CsmGatewayTimeout as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=504)
        except CsmServiceConflict as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=409)
        except CsmUnauthorizedError as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=401)
        except CsmError as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=400)
        except KeyError as e:
            Log.debug(f"Key Error: {e} \n {traceback.format_exc()}")
            message = f"Missing Key for {e}"
            resp = CsmRestApi.error_response(KeyError(message), request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=422)
        except (ServerDisconnectedError, ClientConnectorError, ClientOSError,
                ConcurrentTimeoutError) as e:
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=503)
        except Exception as e:
            Log.critical(f"Unhandled Exception Caught: {e} \n"
                f"{traceback.format_exc()}")
            resp = CsmRestApi.error_response(e, request=request,
                request_id=request.request_id)
            return CsmRestApi.json_response(resp, status=500)

    @staticmethod
    async def _shut_down(loop, site, server=None):
        CsmRestApi.__is_shutting_down = True
        if server is not None:
            original_connections = server.connections.copy()
            for c in original_connections:
                while c in server.connections:
                    await asyncio.sleep(1)
        for task in asyncio.Task.all_tasks():
            if task != asyncio.Task.current_task():
                task.cancel()
        await site.stop()
        loop.stop()

    @staticmethod
    async def _hide_headers(request, response) -> None:
        del response.headers['Server']

    @staticmethod
    async def _handle_sigint(loop, site):
        Log.info('Received SIGINT, shutting down')
        await CsmRestApi._shut_down(loop, site)

    @staticmethod
    async def _handle_sigterm(loop, site, server):
        Log.info('Received SIGTERM, shutting down')
        await CsmRestApi._shut_down(loop, site, server)

    @staticmethod
    def _run_server(app, host=None, port=None, ssl_context=None, access_log=None):
        loop = asyncio.get_event_loop()
        runner = web.AppRunner(app, access_log=access_log)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, host=host, port=port, ssl_context=ssl_context)
        loop.run_until_complete(site.start())
        handlers = {
            signal.SIGINT: lambda: CsmRestApi._handle_sigint(loop, site),
            signal.SIGTERM: lambda: CsmRestApi._handle_sigterm(loop, site, runner.server),
        }
        for k, v in handlers.items():
            loop.add_signal_handler(k, lambda v=v: asyncio.ensure_future(v())),
        print(f'======== CSM agent is running on {site.name} ========')
        print('(Press CTRL+C to quit)', flush=True)
        try:
            loop.run_forever()
        finally:
            loop.close()

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
        CsmRestApi._run_server(
            CsmRestApi._app, port=port, ssl_context=ssl_context, access_log=None)

    # Deprecated Method
    # TODO: remove this code
    # @staticmethod
    # async def process_request(request):
    #     """Receive a request, processes and sends response back to client."""
    #     cmd = request.rel_url.query['cmd']
    #     action = request.rel_url.query['action']
    #     args = request.rel_url.query['args']

    #     request = Request(action, args)
    #     response = CsmApi.process_request(cmd, request)

    #     return response

    @staticmethod
    @CsmAuth.public
    async def process_websocket(request):
        """
        Handle websocket connection.

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
        CsmRestApi._bgtasks.append(app.loop.create_task(CsmRestApi._websock_bg()))
        CsmRestApi._bgtasks.append(app.loop.create_task(CsmRestApi._clear_expired_sessions_bg()))

        # For Sending SSL expiry information to IEM logs below code is required,
        # logic needs to be improved, hence commenting.
        # CsmRestApi._bgtasks.append(app.loop.create_task(CsmRestApi._ssl_cert_check_bg()))

    @staticmethod
    async def _on_shutdown(app):
        Log.debug('REST API shutdown')
        for task in CsmRestApi._bgtasks:
            task.cancel()

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
        except Exception:
            Log.debug('REST API websock broadcast error')

    @classmethod
    async def _ssl_cert_check_bg(cls):
        Log.debug('SSL certificate expiry check background task started')
        try:
            security_service = cls._app[const.SECURITY_SERVICE]
            await security_service.check_certificate_expiry_time_task()
        except AsyncioCancelledError:
            Log.debug('SSL certificate expiry check background task canceled')

        Log.debug('SSL certificate expiry check background task done')

    @classmethod
    async def _clear_expired_sessions_bg(cls):
        Log.info('Started background task for clearing expired sessions')
        try:
            session_mgr_service = cls._app[const.SESSION_MGR_SERVICE]
            await session_mgr_service.clear_sessions()
        except AsyncioCancelledError:
            Log.error('Background task for clearing expired session cancelled')
        Log.info('Background task for clearing expired session done')

    @staticmethod
    async def _async_push(msg):
        return await CsmRestApi._queue.put(msg)

    @staticmethod
    def push(alert):
        coro = CsmRestApi._async_push(alert)
        asyncio.run_coroutine_threadsafe(coro, CsmRestApi._app.loop)
        return True
