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
from typing import ClassVar, Dict, Any

import aiohttp
from dict2xml import dict2xml
from prettytable import PrettyTable

from csm.core.agent.api import CsmApi
from csm.core.blogic import const
from csm.core.providers.providers import Request, Response

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
        self.process_request(cmd.name(), cmd.action(), cmd.options(),
                             cmd.options(),
                             cmd.args(), cmd.method(cmd.action()))
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)

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

    async def process_request(self, session, cmd, action, options, args, method):
        request_url = f"{self._url}/{cmd}"
        rest_obj = RestRequest(request_url, action, session, options, args,
                               method)
        return await rest_obj.get_request()

    async def call(self, cmd):
        async with aiohttp.ClientSession() as session:
            response = await self.process_request(session, cmd.name(),
                                                  cmd.action(), cmd.options(),
                                                  cmd.args(),
                                                  cmd.method(cmd.action()))
        return Response(rc=response[1],
                        output=json.loads(response[0]))

    def __cleanup__(self):
        self._loop.close()

class RestRequest(Request):
    """Cli Rest Request Class """

    def __init__(self, url: str, action: str, session: ClassVar, options: Dict,
                 args: ClassVar, method: str):
        super(RestRequest, self).__init__(args, action)
        self._method = method
        self._url = url
        self._session = session
        self._options = options

    async def _get(self) -> tuple:
        async with self._session.get(self._url, params=self._options) as response:
            return await response.text(), response.status

    async def get_request(self) -> str:
        return await getattr(self, f'_{self._method}')()

class Output:
    """CLI Response Display Class"""

    def __init__(self, response):
        self.rc = response.rc()
        self.output = response.output()

    def dump(self, out, err, output_format, **kwargs) -> None:
        """Dump the Output on CLI"""
        if self.rc != 200:
            return err.write(Output.error(self.rc, self.output))
        if output_format:
            output = getattr(Output, f'dump_{output_format}')(self.output,
                                                              **kwargs)
        else:
            output = str(self.output)
        out.write(output)

    @staticmethod
    def error(rc: int, message: str) -> str:
        """Format for Error message"""
        return f'error({rc}): {message}'

    @staticmethod
    def dump_table(data: Any, headers: Dict, filters: str,
                   **kwargs: Dict) -> str:
        """Format for Table Data"""
        table_obj = PrettyTable()
        table_obj.field_names = headers.values()
        for each_row in data[filters]:
            table_obj.add_row([each_row.get(x) for x in headers.keys()])
        return "{0}".format(table_obj)

    @staticmethod
    def dump_xml(data, **kwargs: Dict) -> str:
        """Format for XML Data"""
        return dict2xml(data)

    @staticmethod
    def dump_json(data, **kwargs: Dict) -> str:
        """Format for Json Data"""
        return json.dumps(data, indent=4, sort_keys=True)
