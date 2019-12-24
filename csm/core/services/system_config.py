#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       Services for SystemConfigSettings handling

 Creation Date:     10/10/2019
 Author:            Soniya Moholkar, Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from typing import List

from csm.common.errors import CsmNotFoundError
from csm.common.queries import SortBy
from csm.common.services import ApplicationService
from csm.core.data.access import Query
from csm.core.data.access.filters import Compare
from csm.core.data.db.db_provider import (DataBaseProvider)
from csm.core.data.models.system_config import SystemConfigSettings

SYSTEM_CONFIG_NOT_FOUND = "system_config_not_found"

class SystemConfigManager:
    """
    The class encapsulates system config management activities.
    """

    def __init__(self, storage: DataBaseProvider) -> None:
        self.storage = storage

    async def create(self,
                     system_config: SystemConfigSettings) -> SystemConfigSettings:
        """
        Stores a new system config
        :param system_config: System config settings model instance
        :returns: System config settings object.
        """
        # TODO Model Validation.
        return await self.storage(SystemConfigSettings).store(system_config)

    async def get_system_config_by_id(self,
                                      config_id: str) -> SystemConfigSettings:
        """
        Fetches system config based on id
        :param config_id: System config identifier
        :returns: System config settings object in case of success. None otherwise.
        """
        query = Query().filter_by(Compare(SystemConfigSettings.config_id, '=',
                                          config_id))
        return next(iter(await self.storage(SystemConfigSettings).get(query)),
                    None)

    async def get_system_config_list(self, offset: int = None, limit: int = None,
                                     sort: SortBy = None) -> List[SystemConfigSettings]:
        """
        Fetches the list of system config.
        :param offset: Number of items to skip.
        :param limit: Maximum number of items to return.
        :param sort: What field to sort on.
        :returns: A list of System Config models
        """
        query = Query()

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        if sort:
            query = query.order_by(getattr(SystemConfigSettings, sort.field),
                                   sort.order)

        return await self.storage(SystemConfigSettings).get(query)

    async def count(self):
        return await self.storage(SystemConfigSettings).count(None)

    async def save(self, system_config: SystemConfigSettings):
        """
        Stores an already existing System config.
        :param system_config: System config settings model instance
        """
        # TODO: validate the model
        await self.storage(SystemConfigSettings).store(system_config)

    async def delete(self, config_id: str) -> None:
        """
        Delete system config based on id
        :param config_id: System config identifier
        """
        await self.storage(SystemConfigSettings).delete(
            Compare(SystemConfigSettings.config_id, \
                    '=', config_id))

class SystemConfigAppService(ApplicationService):
    """
    Service that exposes system config management actions.
    """

    def __init__(self, system_config_mgr: SystemConfigManager):
        self.system_config_mgr = system_config_mgr

    async def create_system_config(self, config_id: str, **kwargs) -> dict:
        """
        Handles the system config creation
        :param config_id: system Config identifier
        :returns: A dictionary describing the newly created system config.
        """
        # TODO Validation
        system_config = SystemConfigSettings.instantiate_system_config(config_id)
        await system_config.update(kwargs)
        await self.system_config_mgr.create(system_config)
        return system_config.to_primitive()

    async def get_system_config_list(self):
        """
        Fetches the list of system config
        :returns: A list of System Config
        """
        system_config_list = await self.system_config_mgr.get_system_config_list()
        if not system_config_list:
            system_config_list = []
        return [system_config.to_primitive() for system_config in
                system_config_list]

    async def get_system_config_by_id(self, config_id: str):
        """
        Fetches a system config based on id
        :param config_id: System config identifier
        :returns: A dict of system config
        """
        system_config = await self.system_config_mgr.get_system_config_by_id(
            config_id)
        if not system_config:
            raise CsmNotFoundError("There is no such system config",
                                   SYSTEM_CONFIG_NOT_FOUND)
        return system_config.to_primitive()

    async def update_system_config(self, config_id: str,
                                   new_values: dict) -> dict:
        """
        Update a system config based on id
        :param config_id: System config identifier
        :returns: A dict of system config
        """
        system_config = await self.system_config_mgr.get_system_config_by_id(
            config_id)
        if not system_config:
            raise CsmNotFoundError("There is no such system config",
                                   SYSTEM_CONFIG_NOT_FOUND)

        await system_config.update(new_values)
        await self.system_config_mgr.save(system_config)
        return system_config.to_primitive()

    async def delete_system_config(self, config_id: str):
        """
        Delete system config based on id
        :param config_id: System config identifier
        :returns: An empty dict
        """
        system_config = await self.system_config_mgr.get_system_config_by_id(
            config_id)
        if not system_config:
            raise CsmNotFoundError("There is no such system config",
                                   SYSTEM_CONFIG_NOT_FOUND)
        await self.system_config_mgr.delete(config_id)
        return {}
