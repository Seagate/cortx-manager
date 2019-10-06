from asyncio import coroutine, Event
from abc import ABC, abstractmethod
from pydoc import locate
from schematics import Model
from schematics.types import DictType, BaseType, StringType, ListType, ModelType
from typing import Type, Dict, List, Union, Callable, Any
from csm.core.blogic.models import CsmModel
from csm.core.blogic.data_access.errors import MalformedConfigurationError, DataAccessInternalError
from csm.core.blogic.data_access.storage import IStorage, AbstractDbProvider
from enum import Enum


class ServiceStatus(Enum):
    NOT_CREATED = "Not created"
    IN_PROGRESS = "In progress"
    READY = "Ready"


class IDatabaseDriver(ABC):
    """
    Interface for database drivers.
    Database drivers are supposed to be responsible for instantiating IStorage objects.
    """
    @abstractmethod
    async def get_storage(self, model, config: dict) -> IStorage:
        pass

    @abstractmethod
    async def create_storage(self, model, config) -> IStorage:
        pass


class DbDriverConfig(Model):
    """
    Database driver configuration description
    """
    import_path = StringType(required=True)
    config = BaseType(default={})  # driver-specific configuration


class DbModelConfig(Model):
    """
    Description of how a specific model is expected to be stored
    """
    import_path = StringType(required=True)
    driver = StringType(required=True)
    # TODO: Discuss: maybe better to use DictType?
    config = BaseType(default={})  # this configuration is db driver-specific


class DbConfig(Model):
    """
    Layout of full database configuration
    """
    drivers = DictType(ModelType(DbDriverConfig), str)
    models = ListType(ModelType(DbModelConfig))


class CachedDatabaseDriver(IDatabaseDriver, ABC):

    """
    Implementation of IDatabaseDriver that allows not to implement storage caching
    """

    def __init__(self):
        self.cache = {}

    def get_storage(self, model, config: dict) -> IStorage:
        if model in self.cache:
            return self.cache[model]
        else:
            raise DataAccessInternalError(f"Storage for {model} is not created")

    @abstractmethod
    async def _create_storage(self, model: Type[CsmModel], config: DbModelConfig):
        """
        Specific Driver storage creation procedure

        :param model:
        :param config:
        :return:
        """
        pass

    async def create_storage(self, model, config) -> None:
        if model not in self.cache:
            storage = await self._create_storage(model, config)
            self.cache[model] = storage


class DbDriverProvider:
    """
    Helper class for database drivers management.
    It is responsible for instantiating database drivers depending on the configuration.
    """
    def __init__(self, driver_config: Dict[str, DbDriverConfig]):
        self.driver_config = driver_config
        self.instances = dict()
        self._driver_status = dict()

    def get_driver(self, key: str) -> IDatabaseDriver:
        """
        Returns a database driver instance depending on the string identifier of
        the driver that was passed as a part of configuration.

        :param key: Database driver key
        :returns: Database driver instance
        """
        if key in self.instances:
            return self.instances[key]
        else:
            raise DataAccessInternalError(f"Driver {key} is not created")

    async def _create_driver(self, key: str) -> IDatabaseDriver:
        if key not in self.driver_config:
            raise MalformedConfigurationError(f"No driver configuration for '{key}'")

        driver = locate(self.driver_config[key].import_path)
        if not driver:
            raise MalformedConfigurationError(f"Cannot import driver class for '{key}'")

        # TODO: consider adding some async drive initialization routine
        return driver(self.driver_config[key].config)

    async def create_driver(self, key: str) -> None:
        self._driver_status[key] = ServiceStatus.IN_PROGRESS
        res = await self._create_driver(key)
        self._driver_status[key] = ServiceStatus.READY
        self.instances[key] = res

    def get_driver_status(self, key: str) -> ServiceStatus:
        return self._driver_status.get(key, ServiceStatus.NOT_CREATED)


class ProxyStorageCallDecorator:

    """Class to decorate proxy call"""

    def __init__(self, async_storage, model: Type[CsmModel], attr_name: str, event: Event):
        self._async_storage = async_storage
        self._model = model
        self._attr_name = attr_name
        self._event = event
        self._proxy_call_coroutine = None

    def __call__(self, *args, **kwargs) -> coroutine:
        async def async_wrapper():
            if self._async_storage.storage_status == ServiceStatus.NOT_CREATED:
                await self._async_storage.create_storage()
                self._event.set()
            elif self._async_storage.storage_status == ServiceStatus.IN_PROGRESS:
                await self._event.wait()

            storage = self._async_storage.get_storage()
            attr = storage.__getattribute__(self._attr_name)
            if callable(attr):
                # may be, first call the function and then check whether we need to await it
                # DD: I think, we assume that all storage API are async
                return await attr(*args, **kwargs)
            else:
                return attr

        self._proxy_call_coroutine = async_wrapper()
        return self._proxy_call_coroutine

    def __del__(self):
        """
        Close proxy call coroutine if it was never awaited

        :return:
        """
        if self._proxy_call_coroutine is not None:
            self._proxy_call_coroutine.close()


# TODO: class can't be inherited from IStorage
class AsyncStorage:

    """
    Decorates all storage async calls and async db drivers and db storages initializations
    """

    def __init__(self, model: Type[CsmModel], model_config: DbModelConfig, driver_provider: DbDriverProvider):
        self._event = Event()
        # TODO: create event for driver creation
        self._model = model
        self._model_config = model_config
        self._storage_status = ServiceStatus.NOT_CREATED
        self._driver_provider = driver_provider

    def __getattr__(self, attr_name: str) -> coroutine:
        _proxy_call = ProxyStorageCallDecorator(self, self._model, attr_name, self._event)
        return _proxy_call

    async def create_storage(self) -> None:
        self._storage_status = ServiceStatus.IN_PROGRESS
        if self._driver_provider.get_driver_status(self._model_config.driver) == ServiceStatus.NOT_CREATED:
            # NOTE: Assume that only one coroutine can create a storage driver and storage
            await self._driver_provider.create_driver(self._model_config.driver)
        driver = self._driver_provider.get_driver(self._model_config.driver)

        await driver.create_storage(self._model, self._model_config.config)
        self._storage_status = ServiceStatus.READY

    def get_storage(self):
        driver = self._driver_provider.get_driver(self._model_config.driver)

        return driver.get_storage(self._model, self._model_config.config)

    @property
    def storage_status(self):
        return self._storage_status


class DbStorageProvider(AbstractDbProvider):

    _cached_async_decorators = dict()  # Global for all DbStorageProvider instances

    def __init__(self, driver_provider: DbDriverProvider, model_config: List[DbModelConfig]):
        self.driver_provider = driver_provider
        self.model_config = {}

        for model in model_config:
            # TODO: improve model loading
            model_class = locate(model.import_path)

            if not model_class:
                raise MalformedConfigurationError(f"Couldn't import '{model.import_path}'")

            if not issubclass(model_class, CsmModel):
                raise MalformedConfigurationError(f"'{model.import_path}'"
                                                  f" must be a subclass of CsmModel")

            self.model_config[model_class] = model

    def get_storage(self, model: Type[CsmModel]):
        if model not in self.model_config:
            raise MalformedConfigurationError(f"No configuration for {model}")

        if model in self._cached_async_decorators:
            return self._cached_async_decorators[model]

        self._cached_async_decorators[model] = AsyncStorage(model, self.model_config[model], self.driver_provider)
        return self._cached_async_decorators[model]
