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

from eos.utils.log import Log
from csm.common.services import ApplicationService
from eos.utils.data.access import Query, SortBy, SortOrder
from csm.core.data.models.node_replace import ReplaceNode, JobStatus


class ReplaceNodeService(ApplicationService):
    def __init__(self, maintanence, provisioner, db):
        """Intantiate Service Class"""
        super(ReplaceNodeService, self).__init__()
        self._maintenance = maintanence
        self._provisioner = provisioner
        self._replace_node = ReplaceNode
        self._storage = db(self._replace_node)

    async def check_status(self):
        """
        Check Current Node Replacement Status
        :return:
        """
        Log.info("Checking Status for Node Replacement")
        sort_by = SortBy(ReplaceNode.created_time, SortOrder.DESC)
        query = Query().order_by(sort_by.field, sort_by.order)
        model = await self._storage.get(query)
        if not model or not  model[0]:
            return {}
        status = JobStatus.Is_Running
        #TODO: Commenting This Since Code from Provisioner is Incomplete
        #status = await self._provisioner.get_provisioner_job_status(model[0].job_id)
        Log.debug(f"old status {status}  new status  {model[0].status}")
        if status != model[0].status:
            setattr(model[0], "status", status)
            await self._storage.store(model[0])
        return model[0].to_primitive()
