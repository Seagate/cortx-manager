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
import inspect
from typing import Callable


class Observable:
    """Observer pattern implementation."""

    def __init__(self):
        """Initialize Observable."""
        self._observers = set()

    def add_listener(self, observer: Callable):
        """
        Add listener to Observable.

        :param observer: observer function.
        :returns: None.
        """
        self._observers.add(observer)

    def remove_listener(self, observer: Callable):
        """
        Remove listener from Observable.

        :param observer: observer to remove.
        :returns: None.
        """
        self._observers.discard(observer)

    def _notify_listeners(self, *args, loop, **kwargs):
        """
        Notify subscribed listeners.

        :param loop: asyncio loop.
        :returns: None.
        """
        for observer in self._observers:
            if inspect.iscoroutinefunction(observer):
                asyncio.run_coroutine_threadsafe(observer(*args, **kwargs), loop=loop)
            else:
                observer(*args, **kwargs)
