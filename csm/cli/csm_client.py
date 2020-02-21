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
import json
import pprint
import sys
import time
import errno
from typing import ClassVar, Dict, Any, Tuple
from importlib import import_module
import aiohttp

from csm.core.agent.api import CsmApi
from csm.core.blogic import const
from csm.core.providers.providers import Request, Response
from csm.common.errors import CsmError, CSM_PROVIDER_NOT_AVAILABLE
from csm.cli.command import Command


class CsmClient:
    """ Base class for invoking business logic functionality """

    def __init__(self, url):
        self._url = url

    def call(self, command):
        pass

    def process_request(self, session, cmd, action, options, args, method):
        pass

class CsmApiClient(CsmClient):
    """ Concrete class to communicate with RAS API, invokes CsmApi directly """

    def __init__(self):
        super(CsmApiClient, self).__init__(None)
        CsmApi.init()

    def call(self, cmd):
        """
        Method Invocation:
        Call remote API method asynchronously. Response is received over the
        callback channel. Here we wait until the response is received.
        TODO: Add a timeout.
        """
        self._response = None
        self.process_request(cmd.name, cmd.action, cmd.options,
                             cmd.options,
                             cmd.args, cmd.get_method(cmd.action))
        while self._response == None:
            time.sleep(const.RESPONSE_CHECK_INTERVAL)

        # TODO - Examine results
        # TODO - Return (return_code, output)
        return self._response

    def process_request(self, session, cmd, options, action, args, method):
        request = Request(action, args)
        CsmApi.process_request(cmd, request, self.process_response)

    def process_response(self, response):
        self._response = response

class CsmDirectClient(CsmClient):
    """Class Handles Direct Calls for CSM CLI"""
    def __init__(self):
        super(CsmDirectClient, self).__init__(None)

    async def call(self, command):
        module_obj = import_module(command.comm.get("target"))
        if command.comm.get("class", None):
            if command.comm.get("is_static", False):
                target = getattr(module_obj, command.comm.get("class"))
            else:
                target = getattr(module_obj, command.comm.get("class"))()
        else:
            target = module_obj
        return getattr(target, command.comm.get("method"))(command)

class CsmRestClient(CsmClient):
    """ REST API client for CSM server """

    def __init__(self, url):
        super(CsmRestClient, self).__init__(url)
        self._session_token = None

    def has_open_session(self):
        return self._session_token is not None

    def _failed(self, respone):
        """
        This check if response failed it will return true else false
        """
        if respone.rc() != 200:
            return True
        return False
    
    async def login(self, username, password):
        response, headers = await self.call(LoginCommand(username, password))
        token = headers.get('Authorization')
        if self._failed(response) or not token:
            return False
        token = token.split(' ')
        if len(token) != 2 or token[0] != 'Bearer' or not token[1]:
            return False
        self._session_token = token[1]
        return True

    async def logout(self):
        response, _ = await self.call(LogoutCommand())
        if self._failed(response):
            return False
        self._session_token = None
        return True

    async def permissions(self):
        url = "/v1/permissions"
        method = "GET"
        headers = {'Authorization': f'Bearer {self._session_token}'} if self._session_token else {}
        async with aiohttp.ClientSession(headers=headers) as session:
            response, _ = await self.process_direct_request(url, session, method, {}, {})
        if self._failed(response):
            raise CsmError(errno.EACCES, 'Could not get permissions from server, check session')
        return response.output()['permissions']


    async def call(self, cmd):
        headers = {'Authorization': f'Bearer {self._session_token}'} if self._session_token else {}
        async with aiohttp.ClientSession(headers=headers) as session:
            body, headers, status = await self.process_request(session, cmd)
        try:
            data = json.loads(body)
        except ValueError:
            if body == '401: Unauthorized':
                raise CsmError(errno.EINVAL, 'You are unauthorized to do this')
            else:
                raise CsmError(errno.EINVAL, 'Could not parse the response')
        return Response(rc=status, output=data), headers

    async def process_request(self, session, cmd):
        rest_obj = RestRequest(self._url, session, cmd)
        body, headers, status = await rest_obj.request()
        return body, headers, status

    async def process_direct_request(self, url, session, method, params_json, body_json):
        url = self._url + url
        rest_obj = DirectRestRequest(url, session, method, params_json, body_json)
        body, headers, status = await rest_obj.request()
        try:
            data = json.loads(body)
        except ValueError:
            if body == '401: Unauthorized':
                raise CsmError(errno.EINVAL, 'You are unauthorized to do this')
            else:
                raise CsmError(errno.EINVAL, 'Could not parse the response')
        return Response(rc=status, output=data), headers

    def __cleanup__(self):
        self._loop.close()


class RestRequest(Request):
    """Cli Rest Request Class """

    def __init__(self, url, session, command):
        super(RestRequest, self).__init__(command.args, command.name)
        self._method = command.method
        self._options = command.options
        self._session = session
        self._rest = command.comm
        self._url = url + command.target

    def format(self, data, key):
        return {k: data.get(k, self._rest[key][k]) for k, v in
                self._rest.get(key, {}).items()}

    async def request(self) -> Tuple:
        try:
            params_json = self.format(self._options, 'params')
            params_json = {k: v for k, v in params_json.items() if v is not None}
            body_json = self.format(self._options, 'json')
            body_json = {k: v for k, v in body_json.items() if v is not None}
            async with self._session.request(method=self._method,
                                             url=self._url.format(**self._rest,
                                                                  **self._options),
                                             params=params_json,
                                             json=body_json,
                                             timeout=const.TIMEOUT) as response:
                return await response.text(), response.headers, response.status
        except aiohttp.ClientConnectionError as exception:
            raise CsmError(CSM_PROVIDER_NOT_AVAILABLE,
                           'Cannot connect to csm agent\'s host {0}:{1}'
                           .format(exception.host, exception.port))


class DirectRestRequest(Request):
    """Cli Rest Request Class """

    def __init__(self, url, session, method, params_json, body_json):
        super(DirectRestRequest, self).__init__(None, None)
        self._url = url
        self._session = session
        self._method = method
        self._params_json = params_json
        self._body_json = body_json

    async def request(self) -> Tuple:
        try:
            print(self._url)
            async with self._session.request(method=self._method,
                                             url=self._url,
                                             params=self._params_json,
                                             json=self._body_json,
                                             timeout=const.TIMEOUT) as response:
                return await response.text(), response.headers, response.status
        except aiohttp.ClientConnectionError as exception:
            raise CsmError(CSM_PROVIDER_NOT_AVAILABLE,
                           'Cannot connect to csm agent\'s host {0}:{1}'
                           .format(exception.host, exception.port))
            
            
class LoginCommand(Command):
    """CLI Default Logout Command"""

    def __init__(self, username, password):
        options = {
            "username": username,
            "password": password,
            "need_confirmation": False,
            "comm": {
                "json": {"username": "",
                         "password": "",
                         },
                "type": "rest",
                "method": "post",
                "target": "/{version}/login",
                "version": "v1"
            },
            "output": {},
            "sub_command_name": "login",
        }
        args = None
        super().__init__('session', options, args)


class LogoutCommand(Command):
    """CLI Default Login Command"""

    def __init__(self):
        options = {
            "need_confirmation": False,
            "comm": {
                "type": "rest",
                "method": "post",
                "target": "/{version}/logout",
                "version": "v1"
            },
            "output": {},
            "sub_command_name": "logout"
        }
        args = None
        super().__init__('session', options, args)
