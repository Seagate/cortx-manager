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

from abc import ABC, abstractmethod
from collections import OrderedDict

class SyncKeyValueStorage(ABC):
    @abstractmethod
    def get(self, key, defval = None):
        pass

    @abstractmethod
    def put(self, key, val):
        pass

    @abstractmethod
    def items(self):
        pass

class SyncInMemoryKeyValueStorage(SyncKeyValueStorage):
    def __init__(self):
        super().__init__()
        self.memdict = OrderedDict()

    def get(self, key, defval=None):
        return self.memdict.get(key, defval)

    def put(self, key, val):
        self.memdict[key] = val

    def items(self):
        return self.memdict.items()

class AsyncKeyValueStorage(ABC):
    @abstractmethod
    async def get(self, key, defval = None):
        pass

    @abstractmethod
    async def put(self, key, val):
        pass

    @abstractmethod
    async def items(self):
        pass

class AsyncInMemoryKeyValueStorage(AsyncKeyValueStorage):
    def __init__(self):
        super().__init__()
        self.memdict = OrderedDict()

    async def get(self, key, defval = None):
        return self.memdict.get(key, defval)

    async def put(self, key, val):
        self.memdict[key] = val

    async def items(self):
        items = self.memdict.items()
        for item in items:
            yield item
