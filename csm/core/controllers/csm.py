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
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from aiohttp import web
from csm.core.agent.api import CsmApi, Request

class CsmCliView(web.View, CsmApi):
    async def get(self):
        cmd = self.request.rel_url.query['cmd']
        action = self.request.rel_url.query['action']
        args = self.request.rel_url.query['args']
        request = Request(action, args)
        response = CsmApi.process_request(cmd, request)
        return response
