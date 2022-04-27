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
from csm.common.plugin import CsmPlugin
from csm.core.blogic import const
from csm.common.ha.cluster_management.operations_factory import ResourceOperationsFactory

class ClusterManagementPlugin(CsmPlugin):
    """
    Communicates with HA via ha_framework to process operations
    on cluster.
    """

    def __init__(self, ha):
        super().__init__()

        self._ha = ha

    def init(self, **kwargs):
        pass

    @Log.trace_method(Log.DEBUG)
    def process_request(self, **kwargs):
        """
        Process the request for operations on cluster and resources in it.
        """
        request = kwargs.get(const.PLUGIN_REQUEST, "")
        operation = kwargs.get(const.ARG_OPERATION, "")

        Log.debug(f"Cluster operations plugin process_request with arguments: {kwargs}")
        process_request_resut = None
        if request == const.PROCESS_CLUSTER_STATUS_REQ:
            node_id = kwargs.get(const.ARG_NODE_ID, "")
            process_request_resut = self._ha.get_cluster_status(node_id)
        elif request == const.PROCESS_CLUSTER_OPERATION_REQ:
            if operation == const.ShUTDOWN_SIGNAL:
                process_request_resut = self._process_shutdown_signal(kwargs)
            else:
                process_request_resut = self._process_cluster_operation(kwargs)
        return process_request_resut

    def _process_cluster_operation(self, filters):
        """
        Operations on cluster.
        """
        resource = filters.get(const.ARG_RESOURCE, "")
        operation = filters.get(const.ARG_OPERATION)
        arguments = filters.get(const.ARG_ARGUMENTS)
        process_result = self._ha.process_cluster_operation(resource, operation,
                                                            **arguments)
        return process_result

    def _process_shutdown_signal(self, kwargs):
        resource = kwargs.get(const.ARG_RESOURCE, "")
        operation = kwargs.get(const.ARG_OPERATION, "")
        ResourceOperationsFactory.get_operations_by_resource(resource)\
                                    .get_operation(operation)\
                                    .execute(None, **kwargs)
        cluster_op_resp = {
            "message": "Shutdown signal sent successfully."
        }
        Log.debug(f"Cluster Operation: {cluster_op_resp}")
        return cluster_op_resp