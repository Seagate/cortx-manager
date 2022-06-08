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

import time
from csm.common.services import ApplicationService
from cortx.utils.conf_store.conf_store import Conf
from csm.core.blogic import const
from cortx.utils.log import Log
from csm.common.comm import MessageBusComm
from csm.common.errors import CsmServiceNotAvailable

class ClusterManagementAppService(ApplicationService):
    """
    Manage operations on cluster and resources in it.
    """

    def __init__(self, plugin):
        self._cluster_management_plugin = plugin
        self.message_bus_obj = None

    def init_message_bus(self):
        self.message_bus_obj = MessageBusComm(Conf.get(const.CONSUMER_INDEX, const.KAFKA_ENDPOINTS),
                                         unblock_consumer=True)
        MAX_RETRY_COUNT = 5
        RETRY_SLEEP_DURATION = 3
        is_kafka_error = False
        for retry in range(0, MAX_RETRY_COUNT):
            is_kafka_error = False
            try:
                self.message_bus_obj.init(type=const.PRODUCER,
                                    producer_id=Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.MSG_BUS_CLUSTER_STOP_PRODUCER_ID),
                                    message_type=Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.MSG_BUS_CLUSTER_STOP_MSG_TYPE),
                                    method=Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.MSG_BUS_CLUSTER_STOP_METHOD))
            except Exception as e:
                Log.error(f"Message bus failing: {e}")
                is_kafka_error = True
                time.sleep(RETRY_SLEEP_DURATION)
            if not is_kafka_error:
                break
        if is_kafka_error:
            Log.error("Kafka Message bus Service not available")
            raise CsmServiceNotAvailable()


    @Log.trace_method(Log.DEBUG)
    async def get_cluster_status(self, node_id):
        """
        Get status of the cluster when node with id{node_i}
        will be stopped or powered off.
        """
        request_params = dict()
        request_params[const.PLUGIN_REQUEST] = const.PROCESS_CLUSTER_STATUS_REQ
        request_params[const.ARG_NODE_ID] = node_id
        Log.debug(f"ClusterOperationsAppService: Making plugin call with arguments: "
                  f"{request_params}")
        plugin_response = self._cluster_management_plugin.process_request(**request_params)
        return plugin_response

    @Log.trace_method(Log.DEBUG)
    async def request_operation(self, resource, operation, **arguments):
        """
        Request operations on cluster and resources in it.
        """
        plugin_request_params = self._build_request_parameters(resource, operation, arguments)
        Log.debug(f"Cluster operation {operation} on {resource} with arguments: \
                    {plugin_request_params}")
        plugin_response = self._cluster_management_plugin.process_request(**plugin_request_params)
        return plugin_response

    def _build_request_parameters(self, resource, operation, arguments):
        """
        Build request parameters based on the arguments.
        """
        request_params = dict()
        request_params[const.PLUGIN_REQUEST] = const.PROCESS_CLUSTER_OPERATION_REQ
        request_params[const.ARG_RESOURCE] = resource
        request_params[const.ARG_OPERATION] = operation
        request_params[const.ARG_ARGUMENTS] = arguments
        if operation == const.ShUTDOWN_SIGNAL:
            request_params[const.ARG_MSG_OBJ] = self.message_bus_obj
        return request_params

