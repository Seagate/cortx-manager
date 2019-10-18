#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          stats.py
 Description:       Sample implementation of stats view

 Creation Date:     10/16/2019
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from .view import CsmView
from aiohttp import web
from csm.core.services.stats import StatsAppService


@CsmView._app_routes.get("/api/v1/stats")
@CsmView._app_routes.view("/api/v1/stats/{stat_id}")
class StatsView(CsmView):
    """
    Sample implementation if stats view
    """

    def __init__(self, request):
        super(StatsView, self).__init__(request)

        """
        If service is created at api.py file it can be accessed 
        this way
        """
        # self._service = self.request.app["stat_service"]

        """
        Following variable need to be populated for default GET REST
        """
        self._service = StatsAppService()
        self._service_dispatch = {
            "get": self._service.get_all,
            "get_specific": self._service.get
        }

    """
    For validation of get parameters this can be overridden 
    """
    # def validate_get(self):
    #     raise ValidationError("Invalid args")

    """
    base provides GET REST implementation. This can be overridden 
    """
    # async def get(self):
    #     response_obj = {"method": self.request.method,
    #                     "path": self.request.path}
    #     return response_obj

    """
    Sample post implementation
    """
    async def post(self):
        response_obj = {
            "method": self.request.method,
            "path": self.request.path}
        return response_obj
