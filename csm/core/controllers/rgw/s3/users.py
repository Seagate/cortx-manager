# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
from marshmallow import Schema, fields, ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from csm.core.controllers.validators import ValidationErrorFormatter

class UserCreateSchema(Schema):
    uid = fields.Str(data_key='uid', required=True)
    display_name = fields.Str(data_key='display-name', required=True)
    email = fields.Str(data_key='email', missing=None)
    key_type = fields.Str(data_key='key-type', missing=None)
    access_key = fields.Str(data_key='access-key', missing=None)
    secrete_key = fields.Str(data_key='secrete-key', missing=None)
    user_caps = fields.Str(data_key='user-caps', missing=None)
    generate_key = fields.Bool(data_key='generate-key', default=True)
    max_buckets = fields.Int(data_key='max-buckets', default=1000)
    suspended = fields.Bool(data_key='suspended', default=False)
    tenant = fields.Str(data_key='tenant', missing=None)

@CsmView._app_routes.view("/api/v2/s3/users")
class UserListView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.RGW_S3_USERS_SERVICE]


    @CsmAuth.permissions({Resource.RGW_S3_USERS: {Action.CREATE}})
    async def post(self):
        """
        POST REST implementation for creating a rgw s3 user
        """
        Log.debug("Handling users post request.")
        try:
            schema = UserCreateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args=f"Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        response = await self._service.create_user(**user_body)
        return response