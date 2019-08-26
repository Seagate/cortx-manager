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

import time
import json
import aiohttp

from csm.core.agent.api import CsmApi
from csm.core.providers.providers import Request, Response
from csm.common.rest import RestRequest
from csm.common.log import Log
from csm.core.blogic import const

class CsmClient:
    """ Base class for invoking business logic functionality """

    def __init__(self, url):
        self._url = url

    def call(self, command):
        pass

    def process_request(self, session, cmd, action, options, args):
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
        self.process_request(cmd.name(), cmd.action(), cmd.options(),cmd.options(),
                             cmd.args())
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)

        # TODO - Examine results
        # TODO - Return (return_code, output)
        return self._response

    def process_request(self, session, cmd, options, action, args):
        request = Request(action, args)
        CsmApi.process_request(cmd, request, self.process_response)

    def process_response(self, response):
        self._response = response


class CsmRestClient(CsmClient):
    """ REST API client for CSM server """
    def __init__(self, url):
        super(CsmRestClient, self).__init__(url)

    async def process_request(self, session, cmd, action, options, args, **kwargs):
        request_url = f"{self._url}/{cmd}/{action}"
        rest_obj = RestRequest(request_url, session, options, args,
                               kwargs.get("method", 'get'))
        return await rest_obj.get_request()

    async def call(self, cmd):
        async with aiohttp.ClientSession() as session:
            response = await self.process_request(session, cmd.name(),
                                                  cmd.action(), cmd.options(),
                                                  cmd.args(), method=cmd.method())
        return Response(rc=0, output=json.loads(response))

    def __cleanup__(self):
        self._loop.close()    

