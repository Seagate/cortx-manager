from abc import ABC, abstractmethod
from csm.core.blogic.data_access.storage import IStorage


class IDatabaseDriver(ABC):
    """
    Interface for database drivers.
    Database drivers are supposed to be responsible for instantiating IStorage objects.
    """
    @abstractmethod
    async def get_storage(self, model) -> IStorage:
        pass


class CachedDatabaseDriver(IDatabaseDriver, ABC):
    """
    Implementation of IDatabaseDriver that allows not to implement storage caching
    """
    def __init__(self):
        self.cache = {}

    async def get_storage(self, model) -> IStorage:
        if model in self.cache:
            return self.cache[model]
        else:
            storage = self.create_storage(model)
            self.cache[model] = storage
            return storage

    @abstractmethod
    async def create_storage(self, model) -> IStorage:
        pass
