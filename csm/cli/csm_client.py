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

import aiohttp
from dict2xml import dict2xml
from prettytable import PrettyTable

from csm.core.agent.api import CsmApi
from csm.core.blogic import const
from csm.core.providers.providers import Request, Response
from csm.common.errors import CsmError, CSM_PROVIDER_NOT_AVAILABLE

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

class CsmRestClient(CsmClient):
    """ REST API client for CSM server """

    def __init__(self, url):
        super(CsmRestClient, self).__init__(url)

    async def process_request(self, session, cmd):
        rest_obj = RestRequest(self._url, session, cmd)
        return await rest_obj.request()

    async def call(self, cmd):
        async with aiohttp.ClientSession() as session:
            response = await self.process_request(session, cmd)
        try:
            data = json.loads(response[0])
        except ValueError:
            raise CsmError(errno.EINVAL, 'Could not parse the response')
        return Response(rc=response[1], output=data)

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
            async with self._session.request(method=self._method,
                                             url=self._url.format(**self._rest,
                                                                  **self._options),
                                             params=self.format(self._options,
                                                                'params'),
                                             json=self.format(self._options,
                                                              'json'),
                                             timeout=const.TIMEOUT) as response:
                return await response.text(), response.status
        except aiohttp.ClientConnectionError as exception:
            raise CsmError(CSM_PROVIDER_NOT_AVAILABLE,
                                  'Cannot connect to csm agent\'s host {0}:{1}'
                                  .format(exception.host, exception.port))

class Output:
    """CLI Response Display Class"""

    def __init__(self, command, response):
        self.command = command
        self.rc = response.rc()
        self.output = response.output()

    def dump(self, out, err, output_type, **kwargs) -> None:
        """Dump the Output on CLI"""
        # Todo: Need to fetch the response messages from a file for localization.
        if self.rc != 200:
            errstr = Output.error(self.rc, kwargs.get("error"), self.output) + '\n'
            err.write(errstr or "")
            return None
        elif output_type:
            output = getattr(Output, f'dump_{output_type}')(self.output,
                                                            **kwargs) + '\n'
            out.write(output)

    @staticmethod
    def dump_success(output: dict, success: str, **kwargs):
        """
        :param output:
        :param success:
        :return:
        """
        return str(success)

    @staticmethod
    def error(rc: int, message: str, stacktrace) -> str:
        """Format for Error message"""
        if message:
            return f'error({rc}): {message}\n'
        return f"error({rc}): Error Found :- {stacktrace.get('message')}"

    @staticmethod
    def dump_table(data: Any, table: Dict, **kwargs: Dict) -> str:
        """Format for Table Data"""
        table_obj = PrettyTable()
        table_obj.field_names = table["headers"].values()
        for each_row in data[table["filters"]]:
            table_obj.add_row([each_row.get(x) for x in table["headers"].keys()])
        return "{0}".format(table_obj)

    @staticmethod
    def dump_xml(data, **kwargs: Dict) -> str:
        """Format for XML Data"""
        return dict2xml(data)

    @staticmethod
    def dump_json(data, **kwargs: Dict) -> str:
        """Format for Json Data"""
        return json.dumps(data, indent=4, sort_keys=True)
