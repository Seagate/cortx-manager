from abc import ABC, abstractmethod
from collections import OrderedDict

class SyncKeyValueStorage(ABC):
    @abstractmethod
    def get(self, key, defval = None):
        ...

    @abstractmethod
    def put(self, key, val):
        ...

    @abstractmethod
    def items(self):
        ...

class SyncInMemoryKeyValueStorage(SyncKeyValueStorage):
    def __init__(self):
        super().__init__()
        self.memdict = OrderedDict()

    def get(self, key, defval = None):
        return self.memdict.get(key, defval)

    def put(self, key, val):
        self.memdict[key] = val

    def items(self):
        return self.memdict.items()

class AsyncKeyValueStorage(ABC):
    @abstractmethod
    async def get(self, key, defval = None):
        ...

    @abstractmethod
    async def put(self, key, val):
        ...

    @abstractmethod
    async def items(self):
        ...

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
