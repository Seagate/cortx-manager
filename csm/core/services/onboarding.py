# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

from enum import Enum
from schematics.exceptions import BaseError
from csm.common.errors import CsmInternalError, InvalidRequest
from csm.common.services import ApplicationService
from cortx.utils.data.access import Query
from cortx.utils.data.db.db_provider import DataBaseProvider
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
