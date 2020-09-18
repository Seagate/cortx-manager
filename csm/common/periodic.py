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
from contextlib import suppress
from datetime import datetime, timezone, timedelta
from typing import Awaitable

from cortx.utils.log import Log


class Periodic:
    """
    Manager for periodic tasks.

    Implements asycio "fire and forget" pattern, i.e. runs the provided
    coroutine every provided period of time.
    """

    def __init__(self, period: float, coro: Awaitable,
                 loop=asyncio.get_event_loop(), *args, **kwargs):
        self.period = timedelta(seconds=period)
        self.coro = coro
        self.args = args
        self.kwargs = kwargs
        self.loop = loop
        self.task = None
        self.at = None

    async def _handler(self) -> None:
        """
        Infinite task executor
        """
        while True:
            # Check if it's time to run the task
            current = datetime.now(timezone.utc)
            delta = (self.at - current).total_seconds()
            if delta > 0:
                await asyncio.sleep(delta)

            # Run the task
            try:
                await self.coro(*self.args, **self.kwargs)
            except asyncio.CancelledError:
                reason = f'Periodic task {self.coro.__qualname__} is cancelled'
                Log.info(reason)
                break
            except Exception as e:
                reason = f"Unhandled exception in periodic coroutine "\
                         f"{self.coro.__qualname__}: {str(e)}"
                Log.error(reason)

            # Schedule the next launch time
            self.at += self.period

    def is_running(self) -> bool:
        """
        Check if the next task execution is pending.
        """
        return self.task is not None

    def start_exact(self, at: datetime) -> None:
        """
        Starts the periodic task execution at a given time.

        :param at: the first time to execute the periodic task.
        """
        if self.is_running():
            return
        self.at = at
        self.task = self.loop.create_task(self._handler())

    def start(self, now: bool = True) -> None:
        """
        Starts the periodic task execution.

        :param now: if False, waits for period before the first execution.
        """
        at = datetime.now(timezone.utc)
        if not now:
            at += self.period
        self.start_exact(at)

    def stop(self) -> None:
        """
        Stops the periodic tasks execution.
        """
        if not self.is_running():
            return
        self.task.cancel()
        with suppress(asyncio.CancelledError, asyncio.TimeoutError):
            self.loop.run_until_complete(self.task)
        self.task = None
        self.at = None
