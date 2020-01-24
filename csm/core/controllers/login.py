#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          session.py
 Description:       Implementation of session view

 Creation Date:     10/16/2019
 Author:            Oleg Babin
                    Alexander Nogikh
                    Artem Obruchnikov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
from csm.common.log import Log
from csm.core.services.sessions import LoginService
from csm.common.errors import InvalidRequest
from .view import CsmView, CsmResponse, CsmAuth


@CsmView._app_routes.view("/api/v1/login")
@CsmAuth.public
class LoginView(CsmView):

    async def post(self):
        try:
            body = await self.request.json()
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body is missing")

        username = body.get('username', None)
        password = body.get('password', None)
        if not username or not password:
            raise InvalidRequest(message_args="Username or password is missing")

        session_id = await self.request.app.login_service.login(username, password)
        if not session_id:
            raise InvalidRequest(message_args="Invalid username or password")

        Log.debug(f'User: {username} successfully logged in.')
        headers = { CsmAuth.HDR: f'{CsmAuth.TYPE} {session_id}' }
        return CsmResponse(headers=headers)


@CsmView._app_routes.view("/api/v1/logout")
class LogoutView(CsmView):

    async def post(self):
        """ We use POST method here instead of GET
        to avoid browser prefetching this URL """
        session_id = self.request.session.session_id
        await self.request.app.login_service.logout(session_id)
        # TODO: Stop any websocket connection corresponding to this session
        Log.info(f'Session ended')
        return CsmResponse()
