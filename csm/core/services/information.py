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

from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.services import ApplicationService
from cortx.utils.schema.release import Release
from csm.common.errors import CsmInternalError, CsmNotFoundError
from csm.core.services.query_deployment.topology_factory import TopologyFactory

class InformationService(ApplicationService):
    """Version Comptibility Validation service class."""

    def __init__(self, topology_config):
        self.config = topology_config

    @Log.trace_method(Log.DEBUG)
    async def check_compatibility(self, **request_body):
        """
        Method to check whether new version are compatible with deployed version

        :param **request_body: Request body kwargs
        """
        Log.debug(f"Request body: {request_body}")
        # Invoke api to check compatibility
        resource = request_body[const.ARG_RESOURCE]
        resource_id = request_body[const.ARG_RESOURCE_ID]
        release = request_body[const.REQUIRES]
        status, reason = Release.is_version_compatible(resource, resource_id, release)

        # handle the response and return
        response = {
            "node_id": request_body.get(const.ARG_RESOURCE_ID),
            "compatible": status,
            "reason": reason
        }
        return response

    @Log.trace_method(Log.DEBUG)
    async def get_topology(self):
        """
        Get topology
        """
        try:
            topology = TopologyFactory.get_instance(self.config)
            response = topology.get()
        except CsmInternalError as e:
            raise e
        return response

    @Log.trace_method(Log.DEBUG)
    async def get_resource(self, resource):
        """
        Fetch list of of resorces of specific type.
        """
        response = await self.get_topology()
        payload  = response[const.TOPOLOGY]
        if isinstance(payload, dict):
            response = {
                const.ID: payload[const.ID],
                resource: payload[resource]
            }
            response[const.TOPOLOGY][resource] = response
        return response

    @Log.trace_method(Log.DEBUG)
    async def get_specific_resource(self, resource, resource_id):
        """
        Query specific resource using id.
        """
        response = await self.get_resource(resource)
        payload = response.get(const.TOPOLOGY).get(resource)
        if isinstance(payload, list):
            response[const.TOPOLOGY][resource] = [item for item in \
                payload if item.get(const.ID) == resource_id]
            if len(response[const.TOPOLOGY][resource]) < 1:
                raise CsmNotFoundError(f"Invalid resource_id: {resource_id}")
        return response
