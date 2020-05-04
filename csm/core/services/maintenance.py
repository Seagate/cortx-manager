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
from typing import Dict
from eos.utils.log import Log
from csm.common.services import Service, ApplicationService
from concurrent.futures import ThreadPoolExecutor
from csm.common.errors import CsmError, CSM_OPERATION_NOT_PERMITTED

class MaintenanceAppService(ApplicationService):
    """
    Provides maintenance services
    """

    def __init__(self, ha):
        super(MaintenanceAppService, self).__init__()
        self._ha = ha
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop = asyncio.get_event_loop()

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
        if not any(map(lambda x : x.get("standby", False),
                       node_status.get('node_status', []))):
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
