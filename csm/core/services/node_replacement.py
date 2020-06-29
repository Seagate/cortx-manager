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
from csm.common.errors import CsmError, CSM_INVALID_REQUEST
from csm.common.services import ApplicationService
from csm.core.blogic import const
from eos.utils.data.access import Query, SortBy, SortOrder
from eos.utils.data.access.filters import Compare
from csm.core.data.models.node_replace import ReplaceNode, JobStatus


class ReplaceNodeService(ApplicationService):
    def __init__(self, maintanence, provisioner, db):
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
        sort_by = SortBy(ReplaceNode.created_time, SortOrder.DESC)
        query = Query().order_by(sort_by.field, sort_by.order)
        model = await self._storage.get(query)
        if not model or not  model[0]:
            return {}
        status = JobStatus.Completed#await self._provisioner.get_provisioner_job_status(model[0].job_id)
        if status != model[0].status:
            setattr(model[0], "status", status)
            await self._storage.store(model[0])
        return model[0].to_primitive()
