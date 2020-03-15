#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          health.py
 Description:       Controllers for health

 Creation Date:     02/18/2020
 Author:            Soniya Moholkar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmAuth

@CsmView._app_routes.view("/api/v1/system/health")
class HealthView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self.health_service = self.request.app["health_service"]        

    @CsmAuth.permissions({Resource.ALERTS: {Action.LIST}})
    async def get(self):
        return await self.health_service.fetch_health_summary()