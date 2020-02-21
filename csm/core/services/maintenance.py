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
from csm.common.log import Log
from csm.common.services import Service, ApplicationService
from concurrent.futures import ThreadPoolExecutor

class MaintenanceAppService(ApplicationService):
    """
    Provides maintenance services
    """

    def __init__(self, ha):
        self._ha = ha
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop = asyncio.get_event_loop()

    async def get_status(self, node) -> Dict:
        """
        Return status of cluster. List of active and passive node
        """
        Log.debug("Get cluster status")
        return await self._loop.run_in_executor(self._executor, self._ha.get_nodes)

    async def shutdown(self, node) -> Dict:
        return {}

    async def stop(self, node) -> Dict:
        """
        Stop node from cluster for maintenance
        """
        return await self._loop.run_in_executor(self._executor, self._ha.make_node_passive, node)

    async def start(self, node) -> Dict:
        """
        Start node monitoring in cluster
        """
        return await self._loop.run_in_executor(self._executor, self._ha.make_node_active, node)
