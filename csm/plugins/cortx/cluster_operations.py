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

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from cortx.utils.log import Log
from csm.common.plugin import CsmPlugin
from csm.common.errors import InvalidRequest
from csm.core.blogic import const


class ClusterOperationsPlugin(CsmPlugin):
    """
    Communicates with HA via ha_framework to process operations
    on cluster.
    """

    def __init__(self, ha):
        super().__init__()

        self._ha = ha
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop = asyncio.get_event_loop()

    def init(self, **kwargs):
        pass

    def process_request(self, **kwargs):
        request = kwargs.get(const.PLUGIN_REQUEST, "")

        Log.debug(f"Cluster operations plugin process_request with arguments: {kwargs}")
        if request == const.PROCESS_CLUSTER_OPERATION_REQ:
            self._process_cluster_operation(kwargs)

        return {"status": "Succeeded"}

    def _process_cluster_operation(self, filters):
        """
        Operations on cluster.
        """
        resource = filters.get(const.ARG_RESOURCE, "")
        resource_id = filters.get(const.ARG_RESOURCE_ID)
        operation = filters.get(const.ARG_OPERATION)
        check_cluster = not filters.get(const.ARG_FORCE)

        self._loop.run_in_executor(self._executor,
                                    partial(self._ha.process_cluster_operation,
                                    resource, resource_id, operation,
                                    check_cluster=check_cluster))

