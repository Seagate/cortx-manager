# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

from csm.common.permission_names import Action, Resource
from csm.common.errors import InvalidRequest
import json
from csm.core.controllers.view import CsmView, CsmAuth
from cortx.utils.log import Log
from csm.core.blogic import const
from marshmallow.exceptions import ValidationError
from marshmallow import Schema, fields, validate

class SupportBundleGenerateSchema(Schema):
    comment = fields.Str(required=True)
    # location = fields.

@CsmView._app_routes.view("/api/v2/support/bundle")
class SupportBundleView(CsmView):
    def __init__(self, request):
        super(SupportBundleView, self).__init__(request)
        self._service = self.request.app[const.SUPPORT_BUNDLE_SERVICE]

    @CsmAuth.permissions({Resource.SUPPORTBUNDLE: {Action.LIST}})
    async def get(self):
        ''' GET REST implementation for fetching support bundle status '''
        Log.debug("Handling unsupported features fetch request")
        bundle_id = self.request.rel_url.query["bundle_id"]
        return await self._service.get_support_bundle_status(bundle_id)

    @CsmAuth.permissions({Resource.SUPPORTBUNDLE: {Action.CREATE}})
    async def post(self):
        ''' POST REST implementation for genearting support bundle '''
        Log.debug("Handling unsupported features fetch request")
        try:
            schema = SupportBundleGenerateSchema()
            user_body = schema.load(await self.request.json(), unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args=f"Request body missing: {jde}")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")

        return await self._service.generate_support_bundle(**user_body)
