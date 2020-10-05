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
from cortx.utils.log import Log
from csm.core.services.sessions import LoginService
from csm.common.errors import InvalidRequest
from .view import CsmView, CsmResponse, CsmAuth
from aiohttp import web


@CsmView._app_routes.view("/api/v1/login")
@CsmAuth.public
class LoginView(CsmView):

    async def post(self):
        try:
            body = await self.request.json()
            Log.debug(f"Handling Login Post request. Username: {body.get('username')}")
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body is missing")

        username = body.get('username', None)
        password = body.get('password', None)
        if not username or not password:
            raise InvalidRequest(message_args="Username or password is missing")

        session_id = await self.request.app.login_service.login(username, password)
        Log.debug(f"Obtained session id for {username}")
        if not session_id:
            raise web.HTTPUnauthorized()

        Log.debug(f'User: {username} successfully logged in.')
        headers = { CsmAuth.HDR: f'{CsmAuth.TYPE} {session_id}' }
        return CsmResponse(headers=headers)


@CsmView._app_routes.view("/api/v1/logout")
class LogoutView(CsmView):

    async def post(self):
        Log.debug(f"Handling Logout Post request. "
                  f"user_id: {self.request.session.credentials.user_id}")
        """ We use POST method here instead of GET
        to avoid browser prefetching this URL """
        session_id = self.request.session.session_id
        await self.request.app.login_service.logout(session_id)
        # TODO: Stop any websocket connection corresponding to this session
        Log.info(f'Session ended')
        return CsmResponse()
