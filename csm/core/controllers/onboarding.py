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
from marshmallow import Schema, fields, validate, validates
from marshmallow.exceptions import ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth


class OnboardingStateSchema(Schema):
    phase = fields.Str(required=True)


@CsmView._app_routes.view("/api/v1/onboarding/state")
@CsmView._app_routes.view("/api/v2/onboarding/state")
class OnboardingStateView(CsmView):

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["onboarding_config_service"]

    async def _validate_request(self, schema):
        try:
            json = await self.request.json()
            body = schema().load(json, unknown='EXCLUDE')
            return body
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Missing request body")
        except ValidationError as e:
            raise InvalidRequest(message_args=f"Invalid request body: {e}")

    @CsmAuth.public
    async def get(self):
        Log.debug("Getting onboarding state")
        phase = await self._service.get_current_phase()
        response = { 'phase': phase }
        return CsmResponse(response)

    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def patch(self):
        Log.debug("Updating onboarding state")
        # TODO: Check if the user has onboarding permissions
        body = await self._validate_request(OnboardingStateSchema)
        await self._service.set_current_phase(body['phase'])
        return CsmResponse()
