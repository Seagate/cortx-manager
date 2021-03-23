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

from .view import CsmView, CsmAuth
from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from cortx.utils.conf_store.conf_store import Conf
from csm.core.blogic import const
from csm.core.controllers.validators import Enum, ValidationErrorFormatter, Server, PortValidator
from marshmallow import (Schema, fields, ValidationError)
from csm.common.permission_names import Resource, Action


class GetMaintenanceSchema(Schema):
    action = fields.Str(required=True, validate=[Enum([const.NODE_STATUS])])

class PostMaintenanceSchema(Schema):
    action_items = [const.SHUTDOWN, const.START, const.STOP]
    resource_name = fields.Str(required=True)
    action = fields.Str(required=True, validate=[Enum(action_items)])
    hostname = fields.Str(missing=True, required=False, validate=[Server()])
    ssh_port = fields.Int(missing=True, required=False, validate=[PortValidator()])

@CsmView._app_routes.view("/api/v1/maintenance/cluster/{action}")
@CsmView._app_routes.view("/api/v2/maintenance/cluster/{action}")
class MaintenanceView(CsmView):
    def __init__(self, request):
        super(MaintenanceView, self).__init__(request)
        self._service = self.request.app[const.MAINTENANCE_SERVICE]
        self.hostname_nodeid_map = Conf.get(const.CSM_GLOBAL_INDEX, f"{const.MAINTENANCE}")
        self.rev_hostname_nodeid_map = {host:node for node, host in self.hostname_nodeid_map.items()}

    @CsmAuth.permissions({Resource.SYSTEM: {Action.LIST}})
    async def get(self):
        """
        Fetch All the Node Current Status.
        """
        Log.debug("Handling maintenance request")
        action = self.request.match_info[const.ACTION]
        try:
            GetMaintenanceSchema().load({const.ACTION: action},
                                        unknown=const.MARSHMALLOW_EXCLUDE)
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        service_action = {
            const.REPLACE_NODE_STATUS: self._service.check_node_replacement_status,
            const.NODE_STATUS: self._service.get_status
        }
        return await service_action[action]()

    @CsmAuth.permissions({Resource.SYSTEM: {Action.UPDATE}})
    async def post(self):
        """
        Process Service Requests for Cluster Shutdown or Node Start Stop.
        :return:
        """
        Log.debug("Handling maintenance request")
        action = self.request.match_info[const.ACTION]
        body = await self.request.json()
        body[const.ACTION] = action

        #if hostname is obtained in request body then get the nodeid mapped to the hostname.
        if self.rev_hostname_nodeid_map.get(body[const.RESOURCE_NAME]):
            body[const.RESOURCE_NAME] = self.rev_hostname_nodeid_map.get(body[const.RESOURCE_NAME])
        try:
            PostMaintenanceSchema().load(body,
                                         unknown=const.MARSHMALLOW_EXCLUDE)
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        if action != const.REPLACE_NODE:
            not_valid_node = await self._service.validate_node_id(body.get(
                const.RESOURCE_NAME), action)
            if not_valid_node:
                raise InvalidRequest(not_valid_node)
        service_action = {
            const.SHUTDOWN: self._service.shutdown,
            const.START: self._service.start,
            const.STOP: self._service.stop,
            const.REPLACE_NODE: self._service.begin_process
        }
        return await service_action[action](**body)
