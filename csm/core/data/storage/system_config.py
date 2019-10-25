"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       storage management for system-config
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

from csm.core.data.models.system_config import ISystemConfigStorage


class SystemConfigStorage(ISystemConfigStorage):
    """
    In memory storage for System Configuration
    """
    def __init__(self, kvs):
        self._kvs = kvs
        self._id = 0

    async def _nextid(self):
        result = self._id
        self._id += 1
        return result

    async def save(self, system_config):
        """
        Saves System Configuration
        :param system_config:
        :return: 200
        """
        key = system_config.key()
        if key is None:
            key = str(await self._nextid())
            system_config.store(key)
        self._kvs.put(key, deepcopy(system_config))

    async def get_all(self):
        """
        Get System configuration
        :return: :type:list
        """
        return list(map(lambda x: x[1], self._kvs.items()))

    async def update(self, system_config):
        """
        update System Configuration
        :param system_config:
        :return: 204
        """
        self._kvs.put(system_config.key(), system_config)
