#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          config.py
 Description:       Services for systemConfig handling

 Creation Date:     10/10/2019
 Author:            Soniya Moholkar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
from typing import Dict

from csm.common.errors import CsmNotFoundError
from csm.common.services import ApplicationService
from csm.core.data.models.system_config import ISystemConfigStorage, SystemConfig

SYSTEMCONFIG_DATA_MSG_NOT_FOUND = "systemconfig_not_found"


class SystemConfigAppService(ApplicationService):
    """
    Provides operations on systemConfig without involving the domain specifics
    """

    def __init__(self, storage: ISystemConfigStorage):
        self._storage = storage

    async def update(self, fields):
        """
        Update the Data of SystemConfig
        :param fields: A dictionary containing fields to update.
        :return:
        """
        system_config_list = await self._storage.get_all()
        if not system_config_list:
            raise CsmNotFoundError("SystemConfig was not found", SYSTEMCONFIG_DATA_MSG_NOT_FOUND)
        system_config = system_config_list[0]

        try:
            if "ipv4" in fields["systemconfig"]["management_network"]:
                system_config.data()["systemconfig"]["management_network"]["ipv4"] = \
                fields["systemconfig"]["management_network"]["ipv4"]

            if "ipv6" in fields["systemconfig"]["management_network"]:
                system_config.data()["systemconfig"]["management_network"]["ipv6"] = \
                fields["systemconfig"]["management_network"]["ipv6"]
        except KeyError as key_error:
            raise CsmNotFoundError(f"SystemConfig was not found {key_error}",
                                   SYSTEMCONFIG_DATA_MSG_NOT_FOUND)

        await self._storage.update(system_config)
        return system_config.data()


    async def save(self, message):
        """
        save the Data of SystemConfig
        :param fields: A dictionary containing fields to update.
        :return:
        """
        system_config = SystemConfig(message)
        await self._storage.save(system_config)
        return system_config.data()

    async def get_all(self, **kwargs) -> Dict:
        """
        Fetch SystemConfig
        :return: :type:dict
        """
        system_config_list = await self._storage.get_all()

        if not system_config_list:
            raise CsmNotFoundError("SystemConfig was not found", SYSTEMCONFIG_DATA_MSG_NOT_FOUND)

        return system_config_list[0].data()
