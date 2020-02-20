#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          storage_capacity.py 
 Description:       Rest API View for getting disk capacity details

 Creation Date:     11/20/2019
 Author:            Udayan Yaragattikar
               

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
from csm.core.providers.providers import Response


@CsmView._app_routes.view("/api/v1/capacity")
class StorageCapacityView(CsmView):
    """
    GET REST API view implementation for getting disk capacity details.
    """
    def __init__(self, request):
        super(StorageCapacityView, self).__init__(request)
        self._service = self.request.app['storage_capacity_service']

    @Log.trace_method(Log.DEBUG)
    async def get(self):
        return await self._service.get_capacity_details()


