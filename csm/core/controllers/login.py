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
from csm.common.errors import InvalidRequest, CsmUnauthorizedError
from .view import CsmView, CsmResponse, CsmAuth
from marshmallow import fields
from marshmallow.exceptions import ValidationError
from csm.core.blogic import const
from csm.core.controllers.validators import ValidationErrorFormatter, ValidateSchema

class LoginSchema(ValidateSchema):
    username = fields.Str(data_key=const.UNAME, required=True)
    password = fields.Str(data_key=const.PASS, required=True)

@CsmView._app_routes.view("/api/v1/login")
@CsmView._app_routes.view("/api/v2/login")
@CsmAuth.public
class LoginView(CsmView):

    async def post(self):
        try:
            schema = LoginSchema()
            request_body = schema.load(await self.request.json())
            username = request_body.get(const.UNAME)
            password = request_body.get(const.PASS)
            Log.info(
                f"Processing request: {self.request.method} {self.request.path}"\
                f" user: {username}")
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(const.JSON_ERROR)
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        session_id, body = await self.request.app.login_service.login(
            username, password)
        if not session_id:
            raise CsmUnauthorizedError("Invalid credentials for user")
        Log.info(f"Login successful. User: {username}")
        headers = {CsmAuth.HDR: f'{CsmAuth.TYPE} {session_id}'}
        return CsmResponse(body, headers=headers)


@CsmView._app_routes.view("/api/v1/logout")
@CsmView._app_routes.view("/api/v2/logout")
class LogoutView(CsmView):

    async def post(self):
        username = self.request.session.credentials.user_id
        Log.info(
            f"Processing request: {self.request.method} {self.request.path}"\
            f" user: {username}")
        session_id = self.request.session.session_id
        await self.request.app.login_service.logout(session_id)
        # TODO: Stop any websocket connection corresponding to this session
        Log.info(f"Logout successful. User: {username}")
        return CsmResponse()
