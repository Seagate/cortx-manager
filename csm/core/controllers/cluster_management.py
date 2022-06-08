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

from marshmallow import Schema, fields, INCLUDE, EXCLUDE, ValidationError
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest, CsmPermissionDenied
from csm.common.permission_names import Resource, Action
from csm.core.blogic import const
from csm.core.controllers.view import CsmView, CsmAuth
from csm.core.controllers.validators import ValidationErrorFormatter, Enum


class ClusterOperationsQueryParameter(Schema):
    arguments_format_values = [const.ARGUMENTS_FORMAT_FLAT, const.ARGUMENTS_FORMAT_NESTED]
    arguments_format = fields.Str(default=const.ARGUMENTS_FORMAT_NESTED,
                                  missing=const.ARGUMENTS_FORMAT_NESTED,
                                  validate=[Enum(arguments_format_values)])


class ClusterOperationsRequestBody(Schema):
    supported_operations = [const.ShUTDOWN_SIGNAL]
    operation = fields.Str(required=True,
                           validate=[Enum(supported_operations)])


@CsmView._app_routes.view("/api/v2/system/management/{resource}")
class ClusterOperationsView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.cluster_management_service = self.request.app[const.CLUSTER_MANAGEMENT_SERVICE]
        if self.cluster_management_service.message_bus_obj is None:
            status = self.cluster_management_service.init_message_bus()
            Log.info(f"Message bus up status {status}")

    @staticmethod
    def _validate_operation(resource: str, operation: str, role: str) -> None:
        """
        Check if the provided operation is allowed for the provided role.

        :param resource: the resource under the operation.
        :param operation: the requested operation.
        :param role: current user's role.
        :returns: None.
        """
        if operation in const.ADMIN_ONLY_OPERATIONS and role != const.CSM_SUPER_USER_ROLE:
            msg = f"Operation '{operation}' can not be performed by the user with role: '{role}'"
            raise CsmPermissionDenied(msg)

    @CsmAuth.permissions({Resource.CLUSTER_MANAGEMENT: {Action.CREATE}})
    async def post(self):
        """Manage resources in cluster."""
        resource = self.request.match_info["resource"]
        qp_schema = ClusterOperationsQueryParameter()
        req_body_schema = ClusterOperationsRequestBody()
        operation = None
        operation_arguments = None
        try:
            qp = qp_schema.load(self.request.rel_url.query, unknown=EXCLUDE)
            req_body = req_body_schema.load(await self.request.json(), unknown=INCLUDE)

            operation = req_body['operation']
            if qp['arguments_format'] == const.ARGUMENTS_FORMAT_FLAT:
                req_body.pop('operation')
                operation_arguments = req_body
            else:
                operation_arguments = req_body['arguments']

            Log.debug(f"Cluster operation {operation} on {resource} "
                      f"with arguments {operation_arguments}. "
                      f"user_id: {self.request.session.credentials.user_id}")
        except ValidationError as val_err:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(val_err)}")
        ClusterOperationsView._validate_operation(
            resource, operation, self.request.session.get_user_role())
        operation_req_result = await self.cluster_management_service.request_operation(
            resource, operation, **operation_arguments)
        return operation_req_result


@CsmView._app_routes.view("/api/v2/system/management/cluster_status/{node_id}")
class ClusterStatusView(CsmView):

    def __init__(self, request):
        super().__init__(request)
        self.cluster_management_service = self.request.app[const.CLUSTER_MANAGEMENT_SERVICE]

    @CsmAuth.permissions({Resource.CLUSTER_MANAGEMENT: {Action.LIST}})
    @Log.trace_method(Log.DEBUG)
    async def get(self):
        """Get cluster status if node with {node_id} is stopped or powered off."""
        node_id = self.request.match_info["node_id"]
        Log.debug(f"ClusterStatusView: Get cluster status due to node: {node_id}")
        cluster_status = await self.cluster_management_service.get_cluster_status(node_id)
        return cluster_status
