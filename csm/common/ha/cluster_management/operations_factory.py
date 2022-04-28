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

from abc import ABC, abstractmethod
from csm.core.blogic import const
from csm.common.errors import InvalidRequest
from csm.common.ha.cluster_management import operations


class ResourceOperations(ABC):
    """
    Base class that all operations factory classes wi.
    """
    @abstractmethod
    def get_operation(self, operation: str) -> operations.Operation:
        raise Exception('get_operation not implemented in ResourceOperations class')


class ClusterOperations(ResourceOperations):
    """
    Factory for Cluster operations.
    """
    def get_operation(self, operation: str) -> operations.Operation:

        clusterOperation = None
        if operation == "start":
            clusterOperation = operations.ClusterStartOperation()
        elif operation == "stop":
            clusterOperation = operations.ClusterStopOperation()
        elif operation == const.ShUTDOWN_SIGNAL:
            clusterOperation = operations.ClusterShutdownSignal()

        if clusterOperation is None:
            raise InvalidRequest(f"Cluster does not support {operation} operation.")

        return clusterOperation


class NodeOperations(ResourceOperations):
    """
    Factory for Node operations.
    """
    def get_operation(self, operation: str) -> operations.Operation:

        nodeOperation = None
        if operation == "start":
            nodeOperation = operations.NodeStartOperation()
        elif operation == "stop":
            nodeOperation = operations.NodeStopOperation()
        elif operation == "poweroff":
            nodeOperation = operations.NodePoweroffOperation()
        elif operation == const.MARK_NODE_FAILURE:
            nodeOperation = operations.NodeFailure()
        if nodeOperation is None:
            raise InvalidRequest(f"Node does not support {operation} operation.")

        return nodeOperation


class ResourceOperationsFactory:
    """
    Factory of operation factories.
    """
    @staticmethod
    def get_operations_by_resource(resource: str) -> ResourceOperations:

        resourceOperations = None
        if resource == 'cluster':
            resourceOperations = ClusterOperations()
        elif resource == 'node':
            resourceOperations = NodeOperations()

        if resourceOperations is None:
            raise InvalidRequest("Invalid resource or the resource does not support any operations.")

        return resourceOperations

