#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          maintenance.py
 Description:       maintenance REST Api

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

from .view import CsmView
from csm.common.log import Log
from csm.common.errors import InvalidRequest

@CsmView._app_routes.view("/api/v1/maintenance/cluster/{action}")
class MaintenanceView(CsmView):
    def __init__(self, request):
        super(MaintenanceView, self).__init__(request)
        self._service = self.request.app["maintenance"]
        self._service_action = {
            "nodes_status": self._service.get_status,
            "shutdown": self._service.shutdown,
            "start": self._service.start,
            "stop": self._service.stop
        }

    async def get(self):
        """
        GET REST implementation for Maintenance request
        """
        #TODO: Changes this api to get list of node
        Log.debug("Handling maintenance request")
        action = self.request.match_info["action"]
        if action in self._service_action.keys():
            node = self.request.rel_url.query.get("node", None)
            return await self._service_action[action](node)
        else:
            raise InvalidRequest("Maintenance Invalid request error ...")
