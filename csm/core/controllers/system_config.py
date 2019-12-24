#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       controllers for system config settings

 Creation Date:     10/14/2019
 Author:            Soniya Moholkar, Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json
import uuid

from csm.common.errors import InvalidRequest
from csm.common.log import Log
from .view import CsmView, CsmAuth

@CsmView._app_routes.view("/api/v1/sysconfig")
class SystemConfigListView(CsmView):
    """
    System Configuration related routes
    """

    def __init__(self, request):
        super(SystemConfigListView, self).__init__(request)
        self._service = self.request.app["system_config_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching user config
    """
    async def get(self):
        Log.debug("Handling system config fetch request")

        return await self._service.get_system_config_list()

    """
    POST REST implementation for creating a system config
    """
    async def post(self):
        Log.debug("Handling system config post request")
        try:
            config_data = await self.request.json()
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        return await self._service.create_system_config(str(uuid.uuid4()),
                                                        **config_data)

@CsmView._app_routes.view("/api/v1/sysconfig/{config_id}")
class SystemConfigView(CsmView):
    def __init__(self, request):
        super(SystemConfigView, self).__init__(request)
        self._service = self.request.app["system_config_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching system config
    """
    async def get(self):
        Log.debug("Handling system config fetch request")

        id = self.request.match_info["config_id"]
        return await self._service.get_system_config_by_id(id)

    """
    PUT REST implementation for creating a system config
    """
    async def put(self):
        Log.debug("Handling system config put request")

        try:
            id = self.request.match_info["config_id"]
            config_data = await self.request.json()
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        return await self._service.update_system_config(id, config_data)
