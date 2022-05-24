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
from marshmallow import Schema, fields, validate
from marshmallow.exceptions import ValidationError
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.core.blogic import const
from csm.core.controllers.rgw.s3.base import S3BaseSchema

class VersionValidationSchema(S3BaseSchema):
    # Define schema here
    required = fields.List(fields.Str, data_key=const.REQUIRED, required=True)

@CsmView._app_routes.view("/api/v2/version/compatibility/{resource}/{resource_id}")
class VersionCompatibilityView(CsmView):
    """
    Version compatiblity validation for REST API implementation.

    POST: Validate version compatibilty
    """
    def __init__(self, request):
        super(VersionCompatibilityView, self).__init__(request)
        self._service = self.request.app[const.VERSION_VALIDATION_SERVICE]

    async def post(self):
        """POST REST implementation for Validating version compatibility."""
        Log.debug(f"Handling POST request.")
        # Read path parameter
        resource_id = self.request.match_info[const.ARG_RESOURCE_ID]
        resource = self.request.match_info[const.ARG_RESOURCE]
        path_params_dict = {
            const.ARG_RESOURCE_ID : resource_id,
            const.ARG_RESOURCE : resource
        }
        # Check for valid Resource
        try:
            # Check for request body schema
            schema = VersionValidationSchema()
            request_body_param = schema.load(await self.request.json())
        except json.decoder.JSONDecodeError:
            raise InvalidRequest("Could not parse request body, invalid JSON received.")
        except ValidationError as val_err:
            raise InvalidRequest("Invalid parameter for request body")
        request_body = {**path_params_dict, **request_body_param}
        # Call Corresponding Service
        with self._guard_service():
            response = await self._service.is_version_compatible(**request_body)
            return CsmResponse(response)
