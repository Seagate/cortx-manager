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

from marshmallow import fields, validate

from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth, CsmResponse
from csm.core.controllers.validators import ValidateSchema
from csm.core.services.activities import ActivityService

from cortx.utils.log import Log


class CreateActivitySchema(ValidateSchema):
    """Create activity schema validation class."""

    name = fields.Str(data_key=const.NAME, required=True)
    resource_path = fields.Str(data_key=const.RESOURCE_PATH, required=True)
    description = fields.Str(data_key=const.DESCRIPTION, required=True)


class UpdateActivityBaseSchema(ValidateSchema):
    """Update activity base schema validation class."""

    status = fields.Str(data_key=const.STATUS_LITERAL, required=True,
                           validate=validate.OneOf(const.SUPPORTED_ACTIVITY_STATUS))
    status_description = fields.Str(data_key=const.STATUS_DESC, required=True)
    pct_progress = fields.Int(data_key=const.PCT_PROGRESS)
    result_code = fields.Int(data_key=const.RESULT_CODE)

class InProgressSchema(ValidateSchema):
    """InProgress activity schema validation class."""

    pct_progress = fields.Int(data_key=const.PCT_PROGRESS,
        validate=validate.Range(min=0, max=99), required=True)
    status_description = fields.Str(data_key=const.STATUS_DESC, required=True)


class SuspendedSchema(ValidateSchema):
    """Suspended activity schema validation class."""

    status_description = fields.Str(data_key=const.STATUS_DESC, required=True)


class CompletedSchema(ValidateSchema):
    """Completed activity schema validation class."""

    pct_progress = fields.Int(data_key=const.PCT_PROGRESS,
        validate=validate.Equal(100))
    result_code = fields.Int(data_key=const.RESULT_CODE, required=True)
    status_description = fields.Str(data_key=const.STATUS_DESC, required=True)


class SchemaFactory:
    @staticmethod
    def init(operation):
        operation_schema_map = {
            const.IN_PROGRESS: InProgressSchema,
            const.COMPLETED: CompletedSchema,
            const.SUSPENDED: SuspendedSchema
        }
        return operation_schema_map[operation]()


@CsmView._app_routes.view("/api/v2/activities")
class ActivitiesListView(CsmView):

    def __init__(self, request):
        super().__init__(request)
        self._activity_service: ActivityService = self.request.app[const.ACTIVITY_MANAGEMENT_SERVICE]

    # Note: Commenting create activity interface.
    # @CsmAuth.permissions({Resource.ACTIVITIES: {Action.CREATE}})
    # async def post(self):
    #     """POST REST implementation for creating a new activity."""
    #     Log.info(f"Handling create an activity POST request"
    #              f" user_id: {self.request.session.credentials.user_id}")
    #     try:
    #         schema = CreateActivitySchema()
    #         request_body = schema.load(await self.request.json())
    #         Log.debug(f"Handling create an activity POST request"
    #                   f" request body: {request_body}")
    #     except json.decoder.JSONDecodeError:
    #         raise InvalidRequest(const.JSON_ERROR)
    #     except ValidationError as val_err:
    #         raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
    #     response = await self._activity_service.create(**request_body)
    #     return CsmResponse(response, const.STATUS_CREATED)


@CsmView._app_routes.view("/api/v2/activities/{id}")
class ActivitiesView(CsmView):

    def __init__(self, request):
        super().__init__(request)
        self._activity_service:ActivityService = self.request.app[const.ACTIVITY_MANAGEMENT_SERVICE]

    @CsmAuth.permissions({Resource.ACTIVITIES: {Action.READ}})
    async def get(self):
        """GET REST implementation for fetching an activity details."""
        Log.info(f"Handling fetch activity details GET request"
                 f" user_id: {self.request.session.credentials.user_id}")
        activity_id = self.request.match_info[const.ID]
        Log.debug(f"Handling fetch activity details GET request"
                  f" with path param: {id}")
        response = await self._activity_service.get_by_id(activity_id)
        return CsmResponse(response)

    # Note: Commenting update activity interface.
    # @CsmAuth.permissions({Resource.ACTIVITIES: {Action.UPDATE}})
    # async def patch(self):
    #     """PATCH REST implementation to update the activity."""
    #     Log.info(f"Handling update ativity PATCH request"
    #              f" user_id: {self.request.session.credentials.user_id}")
    #     activity_id = self.request.match_info[const.ID]
    #     path_params = {const.ID: activity_id}
    #     try:
    #         schema = UpdateActivityBaseSchema()
    #         request_params = schema.load(await self.request.json())
    #         status_val = request_params.get(const.STATUS_LITERAL)
    #         status_schema = SchemaFactory.init(status_val)
    #         _ = status_schema.load(request_params, unknown='EXCLUDE')
    #         Log.debug(f"Handling update activity PATCH request"
    #                   f" with request params: {request_params}")
    #         request_body = {**path_params, **request_params}
    #     except json.decoder.JSONDecodeError:
    #         raise InvalidRequest(const.JSON_ERROR)
    #     except ValidationError as val_err:
    #         raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
    #     response = await self._activity_service.update_by_id(**request_body)
    #     return CsmResponse(response)
