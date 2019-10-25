"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       controllers for system-config
                    repository.

 Creation Date:     10/14/2019
 Author:            Soniya Moholkar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from copy import deepcopy

from csm.core.services.system_config import SystemConfigAppService
from .view import CsmView


@CsmView._app_routes.view("/api/v1/config")
class SystemConfigView(CsmView):
    """
    System Configuration related routes
    """
    def __init__(self, request):
        super(SystemConfigView, self).__init__(request)
        system_config_storage = self.request.app["system_config_storage"]
        self._service = SystemConfigAppService(system_config_storage)
        self._service_dispatch = {
            "get": self._service.get_all
        }

    async def post(self):
        """
        Save System Confuration
        :return: :type:dict
        """
        response_obj = await self._service.save(await self.request.json())
        return response_obj


@CsmView._app_routes.view("/api/v1/networkmanagement")
class ManagementNetwork(SystemConfigView):
    """
    Management Network Settings related routes
    """
    def __init__(self, request):
        super(ManagementNetwork, self).__init__(request)

    async def get(self):
        """
        get Management Network Setting
        :return: :type:dict
        """
        response_obj = await super(SystemConfigView, self).get()
        response = deepcopy(response_obj)
        try:
            response["systemconfig"].pop("data_network_setting")
        except AttributeError as ex:
            print(ex)
        return response

    async def patch(self):
        """
        Updated Management Network Settings
        :return: :type:dict
        """
        body = await self.request.json()
        response_obj = await self._service.update(body)
        response = deepcopy(response_obj)
        try:
            response["systemconfig"].pop("data_network_setting")
        except AttributeError as ex:
            print(ex)
        return response
