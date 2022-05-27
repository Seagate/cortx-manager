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
from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest, CsmInternalError
from csm.core.blogic import const
from csm.common.errors import CsmNotFoundError
from csm.core.controllers.validators import ValidationErrorFormatter

class VersionValidationSchema(Schema):
    # Define schema here
    requires = fields.List(fields.Str, data_key=const.REQUIRES, required=True)

@CsmAuth.public
@CsmView._app_routes.view("/api/v2/version/compatibility/{resource}/{resource_id}")
class VersionInformationView(CsmView):
    """
    Version compatiblity validation for REST API implementation.

    POST: Validate version compatibilty
    """
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.INFORMATION_SERVICE]

    async def post(self):
        """POST REST implementation for Validating version compatibility."""
        Log.info("Handling POST request for Version compatibility Validation.")
        # Read path parameter
        resource_id = self.request.match_info[const.ARG_RESOURCE_ID]
        resource = self.request.match_info[const.ARG_RESOURCE]
        # Check for valid Resource
        if resource not in const.VERSION_RESOURCES:
            raise CsmNotFoundError(f"{resource} is not valid")
        path_params_dict = {
            const.ARG_RESOURCE_ID : resource_id,
            const.ARG_RESOURCE : resource
        }
        try:
            # Check for request body schema
            schema = VersionValidationSchema()
            request_body_param = schema.load(await self.request.json())
        except json.decoder.JSONDecodeError:
            raise InvalidRequest("Could not parse request body, invalid JSON received.")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        request_body = {**path_params_dict, **request_body_param}
        # Call Version Compatibility validation Service
        Log.info("Checking Version compatibility Validation.")
        try:
            response = await self._service.check_compatibility(**request_body)
        except Exception as e:
            Log.error(f"Error in checking compatability: {e}")
            raise CsmInternalError(f"Error in checking compatability: {e}")
        return CsmResponse(response)
