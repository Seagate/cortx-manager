#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          maintenance.py
 Description:       Services for maintenance

 Creation Date:     02/11/2020
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from eos.utils.data.access import Query, SortBy, SortOrder
from eos.utils.log import Log

from csm.common.errors import CSM_OPERATION_NOT_PERMITTED
from csm.common.errors import CsmError, CSM_INVALID_REQUEST
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.data.models.node_replace import ReplaceNode, JobStatus


class MaintenanceAppService(ApplicationService):
    """
    Provides maintenance services
    """

    def __init__(self, ha,  provisioner, db):
        super(MaintenanceAppService, self).__init__()
        self._ha = ha
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop = asyncio.get_event_loop()
        self._provisioner = provisioner
        self._replace_node = ReplaceNode
        self._storage = db(self._replace_node)

    async def get_status(self) -> Dict:
        """
        Return status of cluster. List of active and passive node
        """
        Log.debug("Get cluster status")
        return await self._loop.run_in_executor(self._executor,
                                                self._ha.get_nodes)

    async def shutdown(self, resource_name, **kwargs) -> Dict:
        """
        Shutdown a Node or Cluster.
        :param resource_name:
        :param kwargs:
        :return:
        """
        return await self._loop.run_in_executor(self._executor,
                                                self._ha.shutdown, resource_name)

    async def stop(self, resource_name, **kwargs) -> Dict:
        """
        Stop node from cluster for maintenance
        """
        node_status = await self._loop.run_in_executor(self._executor,
                                                       self._ha.get_nodes)
        if not any(map(lambda x: x.get(const.STANDBY, False),
                       node_status.get(const.NODE_STATUS, []))):
            return await self._loop.run_in_executor(self._executor,
                                                    self._ha.make_node_passive,
                                                    resource_name)
        raise CsmError(rc=CSM_OPERATION_NOT_PERMITTED,
                       desc="Cannot Stop All te Nodes.")

    async def start(self, resource_name, **kwargs) -> Dict:
        """
        Start node monitoring in cluster
        """
        return await self._loop.run_in_executor(self._executor,
                                                self._ha.make_node_active,
                                                resource_name)

    async def check_status(self):
        """
        Check Current Node Replacement Status
        :return:
        """
        Log.info("Checking Status for Node Replacement")
        sort_by = SortBy(ReplaceNode.created_time, SortOrder.DESC)
        query = Query().order_by(sort_by.field, sort_by.order)
        model = await self._storage.get(query)
        if not model or not model[0]:
            return {}
        status = JobStatus.Is_Running
        # TODO: Commenting This Since Code from Provisioner is Incomplete
        # try:
        # status = await self._provisioner.get_provisioner_job_status(model[0].job_id)
        # except Exception as e:
        #     Log.error(f"{e}")

        Log.debug(f"old status {status}  new status  {model[0].status}")
        if status != model[0].status:
            setattr(model[0], "status", status)
            await self._storage.store(model[0])
        return model[0].to_primitive()

    async def _verify_node_status(self, resource_name):
        """
        Verify whether the requested Node is in Shutdown State or Not if Not Ask User to Shut-it Down First.
        :param resource_name: Node ID for Replacing :type Str
        :return:
        """
        try:
            node_status = await self.get_status()
        except CsmError as e:
            Log.error(e)
            return CsmError(rc=CSM_INVALID_REQUEST,
                            desc=const.STATUS_CHECK_FALED)

        resources = node_status.get(const.NODE_STATUS)
        for each_resource in resources:
            if each_resource.get(const.NAME) == resource_name and each_resource.get(const.ONLINE):
                break
        else:
            raise CsmError(rc=CSM_INVALID_REQUEST, desc=const.SHUTDOWN_NODE_FIRST)

    async def begin_process(self, resource_name):
        """
        Start the Node Replacement Process.
        "param: resource_name:  Node ID for Replacing. :type: Str
        """
        # Todo: Commenting Verification Since the BUG EOS-9734 is Already Open.
        # await self._verify_node_status(resource_name)
        # Verify if any Process for Node Replacement is not Running.
        Log.debug("Verifying for Any Running Job")
        if await self.is_job_running():
            raise CsmError(rc=CSM_INVALID_REQUEST,
                           desc=const.NODE_REPLACEMENT_ALREADY_RUNNING)
        # Call Prvisioner API and Start Node Replacement.
        Log.debug("Calling Provisioner API.")
        try:
            job_id = await self._provisioner.start_node_replacement(resource_name)
        except Exception as e:
            # todo: Capture the Error Received From Provisioner And Add Appropriate Exception Classes.
            raise CsmError(rc=CSM_INVALID_REQUEST,
                           desc=f"{e}")
        # Save Received Process ID in Consul.
        model = self._replace_node.generate_new(job_id, resource_name)
        await self._storage.store(model)
        return {"msg": const.NODE_REPLACEMENT_STARTED.format(resource_name=resource_name)}

    async def is_job_running(self):
        """
        Check and Returns True for Running Job else False
        :return: True/False :Boolean
        """
        sort_by = SortBy(ReplaceNode.created_time, SortOrder.DESC)
        query = Query().order_by(sort_by.field, sort_by.order)
        data = await self._storage.get(query)
        if data and data[0].status == JobStatus.Is_Running:
            return True
        return False
