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


class Service:
    def __init__(self):
        super().__init__()
        self._loop = asyncio.get_event_loop()

    def _run_coroutine(self, coro):
        task = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return task.result()


class ApplicationService(Service):
    """A service that is intended to be used by controllers."""

    def __init_(self):
        super().__init__()
