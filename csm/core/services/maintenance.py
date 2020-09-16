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
from typing import Dict

from cortx.utils.data.access import Query, SortBy, SortOrder
from cortx.utils.log import Log

from csm.common.errors import CSM_INVALID_REQUEST, CSM_OPERATION_NOT_PERMITTED, CsmError
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.data.models.node_replace import JobStatus, ReplaceNode


class MaintenanceAppService(ApplicationService):
    """Provides maintenance services"""
    def __init__(self, ha, provisioner, db):
        super().__init__()
        self._ha = ha
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop = asyncio.get_event_loop()
        self._provisioner = provisioner
        self._replace_node = ReplaceNode
        self._storage = db(self._replace_node)
        self._action_map = {
            const.SHUTDOWN: lambda x: not x.get(const.ONLINE),
            const.START: lambda x: not x.get(const.STANDBY),
            const.STOP: lambda x: x.get(const.STANDBY)}

    async def validate_node_id(self, resource_name, action):
        """
        Validate Given Resource ID for System

        :param resource_name: Node ID.
        :param action: Action needed to Validate.
        """

        data = await self.get_status()
        for each_resource in data.get("node_status"):
            if each_resource.get(const.NAME) == resource_name:
                if self._action_map.get(action)(each_resource):
                    return const.RESOURCE_ALREADY_SAME_STATE.format(action=action)
                break
        else:
            return const.INVALID_RESOURCE
        return False

    async def get_status(self) -> Dict:
        """Return status of cluster. List of active and passive node"""
        Log.debug("Get cluster status")
        try:
            return await self._loop.run_in_executor(self._executor, self._ha.get_nodes)
        except Exception as e:
            Log.critical(str(e))
            raise CsmError(rc=CSM_INVALID_REQUEST, desc=const.SERVICE_STATUS_CHECK_FAILED)

    async def shutdown(self, resource_name, **kwargs) -> Dict:
        """Shutdown a Node or Cluster."""
        return await self._loop.run_in_executor(self._executor, self._ha.shutdown, resource_name)

    async def stop(self, resource_name, **kwargs) -> Dict:
        """Stop node from cluster for maintenance"""
        node_status = await self._loop.run_in_executor(self._executor, self._ha.get_nodes)
        if not any(map(lambda x: x.get(const.STANDBY, False),
                       node_status.get(const.NODE_STATUS, []))):
            return await self._loop.run_in_executor(self._executor, self._ha.make_node_passive,
                                                    resource_name)
        raise CsmError(rc=CSM_OPERATION_NOT_PERMITTED, desc="Cannot stop all the nodes.")

    async def start(self, resource_name, **kwargs) -> Dict:
        """Start node monitoring in cluster"""
        return await self._loop.run_in_executor(self._executor, self._ha.make_node_active,
                                                resource_name)

    async def check_node_replacement_status(self):
        """Check Current Node Replacement Status"""
        Log.info("Checking status for node replacement")
        sort_by = SortBy(ReplaceNode.created_time, SortOrder.DESC)
        query = Query().order_by(sort_by.field, sort_by.order)
        model = await self._storage.get(query)
        if not model or not model[0]:
            return {}
        try:
            Log.debug(
                f"Calling provisioner API for fetching status for job id -> {model[0].job_id}")
            status = await self._provisioner.get_provisioner_job_status(model[0].job_id)
            Log.debug(f"old status {model[0].status}  new status -> {status.status}")
        except Exception as e:
            Log.error(f"{e}")
            raise CsmError("Failed to fetch status for running process.")

        if status.status.value != model[0].status:
            setattr(model[0], "status", status.status.value)
            await self._storage.store(model[0])
        return model[0].to_primitive()

    async def _verify_node_status(self, resource_name):
        """
        Verify whether the requested node is in shutdown state or not.
        Ask user to shutdown it first in the latter case.

        :param resource_name: Node ID for replacing :type: Str
        """

        node_status = await self.get_status()
        resources = node_status.get(const.NODE_STATUS)
        for each_resource in resources:
            if each_resource.get(const.NAME) == resource_name:
                if not each_resource.get(const.ONLINE):
                    break
                raise CsmError(rc=CSM_INVALID_REQUEST, desc=const.SHUTDOWN_NODE_FIRST)
        else:
            raise CsmError(rc=CSM_INVALID_REQUEST, desc=const.INVALID_RESOURCE)

    async def begin_process(self, resource_name, hostname=None, ssh_port=None, **kwargs) -> Dict:
        """
        Start the Node Replacement Process.

        :param resource_name: Node ID for Replacing :type: Str
        """

        await self._verify_node_status(resource_name)
        # Verify if any Process for Node Replacement is not Running.
        Log.debug("Verifying for any running job")
        if await self.is_job_running():
            raise CsmError(rc=CSM_INVALID_REQUEST, desc=const.NODE_REPLACEMENT_ALREADY_RUNNING)
        # Call Provisioner API and Start Node Replacement.
        Log.debug(
            f"Begin Node Replacement for {resource_name} with SSH Details -> {hostname}:{ssh_port}")
        try:
            job_id = await self._provisioner.start_node_replacement(
                resource_name, hostname, ssh_port)
        except Exception as e:
            # TODO: Capture the Error Received From Provisioner And
            # Add Appropriate Exception Classes.
            raise CsmError(rc=CSM_INVALID_REQUEST, desc=str(e))
        # Save Received Process ID in Consul.
        model = self._replace_node.generate_new(job_id, resource_name, hostname, ssh_port)
        await self._storage.store(model)
        return {"msg": const.NODE_REPLACEMENT_STARTED.format(resource_name=resource_name)}

    async def is_job_running(self):
        """Check whether job is running or not"""
        sort_by = SortBy(ReplaceNode.created_time, SortOrder.DESC)
        query = Query().order_by(sort_by.field, sort_by.order)
        data = await self._storage.get(query)
        return data and data[0].status == JobStatus.Is_Running
