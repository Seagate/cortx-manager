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

from marshmallow import Schema, fields, ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.validators import ValidationErrorFormatter


class ClusterOperationsQueryParameter(Schema):
    force = fields.Bool(default=False)


@CsmView._app_routes.view("/api/v2/system/management/{resource}/{resource_id}/{operation}")
class ClusterOperationsView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.cluster_operations_service = self.request.app[const.CLUSTER_OPERATIONS_SERVICE]

    @CsmAuth.permissions({Resource.CLUSTER_MANAGEMENT: {Action.LIST}})
    async def get(self):
        """
        Operations on cluster.
        """
        resource = self.request.match_info["resource"]
        resource_id = self.request.match_info["resource_id"]
        operation = self.request.match_info["operation"]
        cluster_operations_view_qp_obj = ClusterOperationsQueryParameter()
        try:
            cluster_operations_view_qp = cluster_operations_view_qp_obj.load(
                                            self.request.rel_url.query,
                                            unknown='EXCLUDE')
            Log.debug(f"Cluster operation {operation} on {resource} with id {resource_id} "
                        f"with query parameters {cluster_operations_view_qp}."
                        f"user_id: {self.request.session.credentials.user_id}")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        operation_req_result = await self.cluster_operations_service\
                                            .request_operation(resource, resource_id,
                                                operation, **cluster_operations_view_qp)
        return operation_req_result

