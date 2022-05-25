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

import json
import time
import errno
from typing import Tuple
import aiohttp

from csm.core.agent.api import CsmApi
from csm.core.blogic import const
from cortx.utils.schema.providers import Request, Response
from csm.common.errors import CsmError, CSM_PROVIDER_NOT_AVAILABLE, CsmUnauthorizedError, CsmServiceNotAvailable
from cortx.utils.cli_framework.client import Client
from cortx.utils.log import Log


class CsmApiClient(Client):
    """Concrete class to communicate with RAS API, invokes CsmApi directly."""

    def __init__(self):
        """Csm Api Client init."""
        super(CsmApiClient, self).__init__(None)
        CsmApi.init()

    def call(self, cmd):
        """
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

class CsmRestClient(Client):
    """REST API client for CSM server"""

    def __init__(self, url):
        """Csm Rest Client init."""
        super(CsmRestClient, self).__init__(url)
        self.not_authorized = "You are not authorized to run cli commands."
        self.could_not_parse = "Could not parse the response"

    @staticmethod
    def _failed(response):
        """
        This check if response failed it will return true else false
        """
        if response.rc() not in  (200, 201):
            return True
        return False

    async def login(self, username, password):
        url = "/v1/login"
        method = const.POST
        body = {"username": username, "password": password}
        try:
            async with aiohttp.ClientSession() as session:
                response, headers = await self.process_direct_request(
                    url, session, method, {}, body)
        except CsmError:
            # during login we want to logout on  any error
            return False
        token = headers.get('Authorization', "").split(' ')
        if CsmRestClient._failed(response) and len(token) != 2 and token[0] != 'Bearer':
            return False
        return token[1]

    async def logout(self, headers):
        url = "/v1/logout"
        method = const.POST
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                _ = await self.process_direct_request(url, session,
                                                                  method, {}, {})
            except Exception as e:
                Log.warn(f"Error while performing logout operation: {e}")
        return True

    async def permissions(self, headers):
        url = "/v1/permissions"
        method = const.GET
        async with aiohttp.ClientSession(headers=headers) as session:
            response, _ = await self.process_direct_request(url, session,
                                                            method, {}, {})
        if CsmRestClient._failed(response):
            raise CsmError(errno.EACCES, 'Could not get permissions from server,'
                                         ' check session')
        return response.output()['permissions']

    async def call(self, cmd, headers=None):
        async with aiohttp.ClientSession(headers=headers) as session:
            body, headers, status = await self.process_request(session, cmd)
        if status == 401:
            raise CsmUnauthorizedError(errno.EACCES, self.not_authorized)
        try:
            data = json.loads(body)
        except ValueError:
            raise CsmError(errno.EINVAL, self.could_not_parse)
        return Response(rc=status, output=data), headers

    async def process_request(self, session, cmd):
        rest_obj = RestRequest(self._url, session, cmd)
        body, headers, status = await rest_obj.request()
        return body, headers, status

    async def process_direct_request(self, url, session, method, params_json,
                                     body_json):
        url = f"{self._url}{url}"
        rest_obj = DirectRestRequest(url, session, method, params_json, body_json)
        body, headers, status = await rest_obj.request()
        if status == 401:
            raise CsmUnauthorizedError(errno.EACCES, self.not_authorized)
        try:
            data = json.loads(body)
        except ValueError:
            raise CsmError(errno.EINVAL, self.could_not_parse)
        return Response(rc=status, output=data), headers

    def __cleanup__(self):
        """Csm Rest Client cleanup."""
        self._loop.close()

class RestRequest(Request):
    """Cli Rest Request Class."""

    def __init__(self, url, session, command):
        """Cli Rest Request init."""
        super(RestRequest, self).__init__(command.args, command.name)
        self._method = command.method
        self._options = command.options
        self._session = session
        self._rest = command.comm
        self._url = url + command.target

    def format(self, data, key):
        return {k: data.get(k, self._rest[key][k]) for k in
                self._rest.get(key, {})}

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
            raise CsmServiceNotAvailable(CSM_PROVIDER_NOT_AVAILABLE,
                           'Cannot connect to csm agent\'s host {0}:{1}'
                           .format(exception.host, exception.port))

class DirectRestRequest(Request):
    """Cli Rest Request Class."""

    def __init__(self, url, session, method, params_json, body_json):
        """Direct Rest Request init."""
        super(DirectRestRequest, self).__init__(None, None)
        self._url = url
        self._session = session
        self._method = method
        self._params_json = params_json
        self._body_json = body_json

    async def request(self) -> Tuple:
        try:
            async with self._session.request(method=self._method,
                                             url=self._url,
                                             params=self._params_json,
                                             json=self._body_json,
                                             timeout=const.TIMEOUT) as response:
                return await response.text(), response.headers, response.status
        except aiohttp.ClientConnectionError as exception:
            raise CsmServiceNotAvailable(CSM_PROVIDER_NOT_AVAILABLE,
                           'Cannot connect to csm agent\'s host {0}:{1}'
                           .format(exception.host, exception.port))
