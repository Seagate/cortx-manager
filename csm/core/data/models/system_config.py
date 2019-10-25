"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       Contains the system-config model and the interface for system-config
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

from abc import ABC, abstractmethod
from datetime import datetime


# the class, rather than storing System-config as a dictionary in the _data field
class SystemConfig:
    """
    Represents an system-config to be sent to front end
    """

    def __init__(self, data):
        self._key = "system_config"
        self._data = data

    def key(self):
        """
        Method to get key
        :return: :type:string
        """
        return self._key

    def data(self):
        """
        Method to get data
        :return: :type:json
        """
        return self._data


# TODO: Consider a more generic approach to storage interfaces
class ISystemConfigStorage(ABC):
    """
    Interface for SystemConfig repository
    """
    @abstractmethod
    async def save(self, system_config: SystemConfig):
        """
        Store an systemConfig.
        :param system_config: SystemConfig object
        :return: nothing
        """

    @abstractmethod
    async def update(self, system_config: SystemConfig):
        """
        Saves the systemConfig object
        :param system_config: SystemConfig object
        :return: nothing
        """

    @abstractmethod
    async def get_all(self) -> list:
        """
        Retrieves the system config
        """
