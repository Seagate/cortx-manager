#!/usr/bin/python

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
from csm.api.api import CsmApi
from csm.providers.providers import Request, Response
from csm.common.log import Log
from csm.common import const

class ApiClient(object):
    """ Base class for invoking business logic functionality """

    def __init__(self, server):
        self._server = server


class CsmApiClient(ApiClient):
    """ Concrete class to communicate with RAS API, invokes CsmApi directly """

    def __init__(self):
        super(CsmApiClient, self).__init__(None)
        CsmApi.init()

    def call(self, command):
        """
        Method Invocation:
        Call remote API method asynchronously. Response is received over the
        callback channel. Here we wait until the response is received.
        TODO: Add a timeout.
        """
        self._response = None
        request = Request(command.action(), command.args().args)
        self.process_request(command.name(), request)
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)

        # TODO - Examine results
        # TODO - Return (return_code, output)
        return self._response

    def process_request(self, command_name, request):
        CsmApi.process_request(command_name, request, self.process_response)

    def process_response(self, response):
        self._response = response


class CsmRestClient(ApiClient):
    """ REST API client for CSM server """
    pass        # TODO - To be implemented
