#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          onboarding.py
 Description:       Onboarding service

 Creation Date:     12/06/2019
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from enum import Enum
from schematics.exceptions import BaseError
from csm.common.errors import CsmInternalError, InvalidRequest
from csm.common.services import ApplicationService
from csm.core.data.access import Query
from csm.core.data.db.db_provider import DataBaseProvider
from csm.core.data.models.onboarding import OnboardingConfig


class OnboardingConfigService(ApplicationService):

    MSGID_DB_ERROR = 'onboarding_db_error'
    MSGID_INVALID_PHASE = 'onboarding_invalid_phase'

    def __init__(self, db: DataBaseProvider):
        self._storage = db(OnboardingConfig)

    async def _load(self) -> OnboardingConfig:
        config = None
        try:
            query = Query().limit(1)
            result = await self._storage.get(query)
            config = next(iter(result), None)
        except:
            raise CsmInternalError('Internal DataBase Error',
                                   self.MSGID_DB_ERROR)
        config = config or OnboardingConfig()
        return config

    async def _store(self, config: OnboardingConfig):
        try:
            await self._storage.store(config)
        except:
            raise CsmInternalError('Internal DataBase Error',
                                   self.MSGID_DB_ERROR)

    async def get_current_phase(self) -> str:
        """
        Fetch current onboarding phase
        :return: :type:str
        """

        config = await self._load()
        return config.phase

    async def set_current_phase(self, phase: str):
        """
        Update current onboarding phase
        :param phase: Next onboarding phase
        """

        config = await self._load()
        config.phase = phase
        try:
            config.validate()
        except BaseError as e:
            raise InvalidRequest('Invalid onboarding phase',
                                 self.MSGID_INVALID_PHASE,
                                 phase)
        await self._store(config)
