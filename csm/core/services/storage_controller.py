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

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from eos.utils.data.access import Query, SortBy, SortOrder
from eos.utils.log import Log
from csm.common.errors import CsmNotImplemented
from csm.common.errors import CsmError, CSM_INVALID_REQUEST
from csm.common.services import ApplicationService
from csm.core.blogic import const


class StorageControllerAppService(ApplicationService):
    """
    Provides maintenance services
    """

    def __init__(self):
        super(StorageControllerAppService, self).__init__()
        self._action_map = {
            const.START: lambda x : not x.get(const.STANDBY),
            const.STOP: lambda x: x.get(const.const.STANDBY)}

    async def get_status(self) -> Dict:
        """
        Return status of stroage controller
        """
        Log.debug("Get stroage controller status")
        raise CsmNotImplemented(f"Storage controller status integration pending")

    async def stop(self, **kwargs) -> Dict:
        """
        Stop stroage controller
        """
        Log.debug("Get stroage controller status")
        raise CsmNotImplemented(f"Storage controller stop integration pending")

    async def start(self, **kwargs) -> Dict:
        """
        Start storage controller
        """
        Log.debug("Get stroage controller status")
        raise CsmNotImplemented(f"Storage controller start integration pending")
