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
import base64
import errno
import yaml
import asyncio
import json
import traceback
import ssl
import time
import uuid
from concurrent.futures import CancelledError as ConcurrentCancelledError
from asyncio import CancelledError as AsyncioCancelledError
from weakref import WeakSet
from aiohttp import web, web_exceptions
from abc import ABC
from ipaddress import ip_address
from secure import SecureHeaders
from typing import Dict, Tuple
from csm.core.blogic.models.audit_log import CsmAuditLogModel
from csm.core.providers.provider_factory import ProviderFactory
from csm.core.providers.providers import Request, Response
from csm.core.services.sessions import LoginService
from csm.common.observer import Observable
from csm.common.payload import *
from cortx.utils.conf_store.conf_store import Conf
from csm.common.conf import  ConfSection, DebugConf
from cortx.utils.log import Log
from cortx.utils.product_features import unsupported_features
from csm.common.payload import Json
from csm.common.services import Service
from csm.core.blogic import const
from csm.common.cluster import Cluster
from csm.common.errors import (CsmError, CsmNotFoundError, CsmPermissionDenied,
                               CsmInternalError, InvalidRequest, ResourceExist,
                               CsmNotImplemented, CsmServiceConflict, CsmGatewayTimeout)
from csm.core.routes import ApiRoutes
from csm.core.services.alerts import AlertsAppService
from csm.core.services.usl import UslService
from csm.core.services.file_transfer import DownloadFileEntity
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.core.controllers import CsmRoutes
from cortx.utils.data.access import Query
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
import re


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

    __unsupported_features = None

    @staticmethod
    def init(alerts_service):
        CsmApi.init()
        CsmRestApi._queue = asyncio.Queue()
        CsmRestApi._bgtasks = []
        CsmRestApi._wsclients = WeakSet()

        CsmRestApi._app = web.Application(
            middlewares=[CsmRestApi.set_secure_headers,
                         CsmRestApi.rest_middleware,
                         CsmRestApi.session_middleware,
                         CsmRestApi.permission_middleware]
        )

        CsmRoutes.add_routes(CsmRestApi._app)
        ApiRoutes.add_websocket_routes(
            CsmRestApi._app.router, CsmRestApi.process_websocket)

        CsmRestApi._app.on_startup.append(CsmRestApi._on_startup)
        CsmRestApi._app.on_shutdown.append(CsmRestApi._on_shutdown)

    @staticmethod
    def is_debug(request) -> bool:
        return 'debug' in request.rel_url.query

    @staticmethod
    def generate_audit_log_string(request, request_id: uuid.UUID, **kwargs):
        if (getattr(request, "session", None) is not None
                and getattr(request.session, "credentials", None) is not None):
            user = request.session.credentials.user_id
        else:
            user = None
        remote_ip = request.remote
        forwarded_for_ip = str(request.headers.get('X-Forwarded-For')).split(',', 2)[0].strip()
        try:
            ip_address(forwarded_for_ip)
        except ValueError:
            forwarded_for_ip = None
        path = request.path
        method = request.method
        user_agent = request.headers.get('User-Agent')
        entry = {
            'user': user if user else "",
            'remote_ip': remote_ip,
            'forwarded_for_ip': forwarded_for_ip if forwarded_for_ip else "",
            'method': method,
            'path': path,
            'user_agent': user_agent,
            'response_code': kwargs.get("response_code", ""),
            'request_id': str(request_id),
            'payload': kwargs.get("payload", "")
        }
        return json.dumps(entry)

    @staticmethod
    def process_audit_log(request, request_id: uuid.UUID, **kwargs):
        url = request.path
        if (not request.app[const.USL_POLLING_LOG]
                and url.startswith('/usl/')
                and not url.endswith('/registerDevice')):
            return
        entry = CsmRestApi.generate_audit_log_string(request, request_id, **kwargs)
        Log.audit(f'{entry}')

    @staticmethod
    def error_response(err: Exception, request_id: uuid.UUID, **kwargs) -> dict:
        resp = {
            "message": None,
            "error_code": None,
            "request_id": str(request_id),
        }

        request = kwargs.get("request")
        if CsmRestApi.is_debug(request):
            resp["stacktrace"] = traceback.format_exc().splitlines()

        if isinstance(err, CsmError):
            resp["error_code"] = err.rc()
            resp["message"] = err.error()
            message_id = err.message_id()
            if message_id is not None:
                resp["message_id"] = err.message_id()
            message_args = err.message_args()
            if message_args is not None:
                resp["error_format_args"] = err.message_args()
        elif isinstance(err, web_exceptions.HTTPError):
            resp["message"] = str(err)
            resp["error_code"] = err.status
        else:
            resp["message"] = f'{str(err)}'
        error_details = kwargs.get("error_details")
        if error_details is not None:
            resp["error_details"] = error_details
        CsmRestApi.process_audit_log(
            request,
            request_id=request_id,
            response_code=resp['error_code'],
            payload=kwargs.get("payload"),
        )
        return resp

    @staticmethod
    def _json_to_url(json: str) -> str:
        data = json.encode('utf-8')
        b64_data = base64.b64encode(data).decode('utf-8')
        return f'data:application/json;base64,{b64_data}'

    @staticmethod
    def _error_to_uuid5(method: str, endpoint: str, exception: Exception) -> uuid.UUID:
        d = {
            'method': method,
            'endpoint': endpoint,
            'exception': repr(type(exception)),
        }
        j = json.dumps(d, sort_keys=True)
        url = CsmRestApi._json_to_url(j)
        return uuid.uuid5(uuid.NAMESPACE_URL, url)

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
        raise web.HTTPUnauthorized(headers=CsmAuth.UNAUTH)

    @staticmethod
    async def _resolve_handler(request):
        match_info = await request.app.router.resolve(request)
        return match_info.handler

    @staticmethod
    async def _is_public(request):
        handler = await CsmRestApi._resolve_handler(request)
        return CsmView.is_public(handler, request.method)

    @classmethod
    async def _get_permissions(cls, request):
        handler = await CsmRestApi._resolve_handler(request)
        return CsmView.get_permissions(handler, request.method)

    @classmethod
    async def get_unsupported_features(cls):
        if cls.__unsupported_features is None:
            db = unsupported_features.UnsupportedFeaturesDB()
            cls.__unsupported_features = await db.get_unsupported_features()
        return cls.__unsupported_features

    @classmethod
    async def is_feature_supported(cls, component, feature):
        unsupported_features = await cls.get_unsupported_features()
        for entry in unsupported_features:
            if (
                component == entry[const.COMPONENT_NAME] and
                feature == entry[const.FEATURE_NAME]
            ):
                return False
        return True

    @classmethod
    async def check_for_unsupported_endpoint(cls, request):
        """
        Check whether the endpoint is supported. If not, send proper error
        reponse.
        """
        def getMatchingEndpoint(endpoint_map, path):
            for key,value in endpoint_map.items():
                map_re = f'^{key}$'.replace("*", "[\w\d]*")
                if re.search(rf"{map_re}", path):
                    return value

        feature_endpoint_map = Json(const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
        endpoint = getMatchingEndpoint(feature_endpoint_map, request.path)
        if endpoint:
            if endpoint[const.DEPENDENT_ON]:
                for component in endpoint[const.DEPENDENT_ON]:
                    if not await cls.is_feature_supported(component, endpoint[const.FEATURE_NAME]):
                        Log.debug(f"The request {request.path} of feature {endpoint[const.FEATURE_NAME]} is not supported by {component}")
                        raise InvalidRequest("This feature is not supported on this environment.")
            if not await cls.is_feature_supported(const.CSM_COMPONENT_NAME, endpoint[const.FEATURE_NAME]):
                Log.debug(f"The request {request.path} of feature {endpoint[const.FEATURE_NAME]} is not supported by {const.CSM_COMPONENT_NAME}")
                raise InvalidRequest("This feature is not supported on this environment.")
        else:
            Log.debug(f"Feature endpoint is not found for {request.path}")

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
        Log.info(f'Username: {session.credentials.user_id}')
        return session

    @staticmethod
    @web.middleware
    async def session_middleware(request, handler):
        session = None
        is_public = await CsmRestApi._is_public(request)
        Log.debug(f'{"Public" if is_public else "Non-public"}: {request}')
        try:
            session_id = CsmRestApi._extract_bearer(request.headers)
            session = await CsmRestApi._validate_bearer(request.app.login_service, session_id)
            Log.info(f'Username: {session.credentials.user_id}')
        except CsmNotFoundError as e:
            if not is_public:
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
            request_id = uuid.uuid4()
            request_timestamp = int(1000 * time.time())
            request_body = dict(request.rel_url.query) if request.rel_url.query else {}
            if not request_body and request.content_length and request.content_length > 0:
                try:
                    request_body = await request.json()
                except Exception as e:
                    request_body = {}
                if request_body:
                    for key in list(request_body.keys()):
                        lower_key = key.lower()
                        if lower_key.find("password") > -1 or \
                            lower_key.find("passwd") > -1 or \
                            lower_key.find("secret") > -1    :
                            del(request_body[key])
            payload = json.dumps(request_body)
            await CsmRestApi.check_for_unsupported_endpoint(request)
            resp = await handler(request)
            if isinstance(resp, DownloadFileEntity):
                file_resp = web.FileResponse(resp.path_to_file)
                file_resp.headers['Content-Disposition'] = f'attachment; filename="{resp.filename}"'
                return file_resp

            if isinstance(resp, web.StreamResponse):
                CsmRestApi.process_audit_log(request, response_code = resp.status, \
                    request_id = request_id, payload=payload)
                return resp

            status = 200
            if isinstance(resp, Response):
                resp_obj = {'message': resp.output()}
                status = resp.rc()
                if not 200 <= status <= 299:
                    Log.error(f"Error: ({status}):{resp_obj['message']}")
            else:
                resp_obj = resp
            CsmRestApi.process_audit_log(request, response_code = status, \
                request_id = request_id, payload=payload)
            return CsmRestApi.json_response(resp_obj, status)
        # todo: Changes for handling all Errors to be done.

        # These exceptions are thrown by aiohttp when request is cancelled
        # by client to complete task which are await use atomic
        except (ConcurrentCancelledError, AsyncioCancelledError) as e:
            Log.warn(f"Client cancelled call for {request.method} {request.path}")
            return CsmRestApi.json_response("Call cancelled by client", status=499)
        except web.HTTPException as e:
            Log.error(f'HTTP Exception {e.status}: {e.reason}')
            raise e
        except InvalidRequest as e:
            Log.error(f"Error: {e} \n {traceback.format_exc()}")
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=400)
        except CsmNotFoundError as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=404)
        except CsmPermissionDenied as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=403)
        except ResourceExist  as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id),
                                            status=const.STATUS_CONFLICT)
        except CsmInternalError as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=500)
        except CsmNotImplemented as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=501)
        except CsmGatewayTimeout as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=504)
        except CsmServiceConflict as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=409)
        except (CsmError, InvalidRequest) as e:
            return CsmRestApi.json_response(CsmRestApi.error_response(e, request = request, request_id = request_id), status=400)
        except KeyError as e:
            Log.error(f"Error: {e} \n {traceback.format_exc()}")
            message = f"Missing Key for {e}"
            return CsmRestApi.json_response(CsmRestApi.error_response(KeyError(message), request = request, request_id = request_id), status=422)
        except Exception as e:
            new_exception = CsmInternalError(desc='a general internal failure has occurred')
            correlation_id = CsmRestApi._error_to_uuid5(
                method=request.method, endpoint=request.path, exception=e)
            log_msg = (f'Unhandled exception caught\n'
                f'Request ID: {request_id} @ {request_timestamp}\n'
                f'Correlation ID: {correlation_id}\n'
                f'Method: {request.method} {request.path}\n')
            error_details = {
                'correlation_id': correlation_id,
                'timestamp': request_timestamp,
                'is_reportable': True,
            }
            Log.critical(log_msg, exc_info=True)
            error_response = CsmRestApi.error_response(
                new_exception, request=request, request_id=request_id, error_details=error_details)
            return CsmRestApi.json_response(error_response, status=500)

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

        web.run_app(CsmRestApi._app, port=port, ssl_context=ssl_context, access_log=None)

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
        CsmRestApi._bgtasks.append(app.loop.create_task(CsmRestApi._websock_bg()))
        CsmRestApi._bgtasks.append(app.loop.create_task(CsmRestApi._ssl_cert_check_bg()))

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
        except:
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
