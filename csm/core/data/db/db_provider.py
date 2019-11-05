#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          db_provider.py
 _description:      Generic Database Implementation

 Creation Date:     6/10/2019
 Author:            Dmitry Didenko
                    Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from asyncio import coroutine
from pydoc import locate
from enum import Enum
from threading import Event
from typing import Type

from schematics import Model
from schematics.types import DictType, StringType, ListType, ModelType, IntType

from csm.core.blogic.models import CsmModel
from csm.common.errors import MalformedConfigurationError, DataAccessInternalError
from csm.core.data.access.storage import AbstractDataBaseProvider

import csm.core.data.db as db_module


DEFAULT_HOST = "127.0.0.1"


class ServiceStatus(Enum):
    NOT_CREATED = "Not created"
    IN_PROGRESS = "In progress"
    READY = "Ready"


class DBSettings(Model):
    """
    Settings for database server
    """

    host = StringType(required=True, default=DEFAULT_HOST)
    port = IntType(required=True, default=None)
    login = StringType()
    password = StringType()


class DBConfig(Model):
    """
    Database driver configuration description
    """

    import_path = StringType(required=True)
    config = ModelType(DBSettings)  # db-specific configuration


class ModelSettings(Model):
    """
    Configuration for CSM model like collection as example
    """
    collection = StringType(required=True)


class DBModelConfig(Model):
    """
    Description of how a specific model is expected to be stored
    """

    import_path = StringType(required=True)
    database = StringType(required=True)
    # this configuration is specific for each supported by model db driver
    config = DictType(ModelType(ModelSettings), str)


class GeneralConfig(Model):
    """
    Layout of full database configuration
    """

    databases = DictType(ModelType(DBConfig), str)
    models = ListType(ModelType(DBModelConfig))


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
                # Note: Should be called once
                await self._async_storage.create_database()
                self._event.set()
            elif self._async_storage.storage_status == ServiceStatus.IN_PROGRESS:
                await self._event.wait()

            database = self._async_storage.get_database()
            if database is None:
                raise DataAccessInternalError("Database is not created")
            attr = database.__getattribute__(self._attr_name)
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


# TODO: class can't be inherited from IDataBase
class AsyncDataBase:
    """
    Decorates all storage async calls and async db drivers and db storages initializations
    """

    def __init__(self, model: Type[CsmModel], model_config: DBModelConfig,
                 db_config: GeneralConfig):
        self._event = Event()
        self._model = model
        self._model_settings = model_config.config.get(model_config.database)
        self._db_config = db_config.databases.get(model_config.database)
        self._database_status = ServiceStatus.NOT_CREATED
        self._database_module = getattr(db_module, self._db_config.import_path)
        self._database = None

    def __getattr__(self, attr_name: str) -> coroutine:
        _proxy_call = ProxyStorageCallDecorator(self, self._model, attr_name, self._event)
        return _proxy_call

    async def create_database(self) -> None:
        self._database_status = ServiceStatus.IN_PROGRESS
        self._database = await self._database_module.create_database(self._db_config.config,
                                                                     self._model_settings.collection,
                                                                     self._model)
        self._database_status = ServiceStatus.READY

    def get_database(self):
        # Note: database can be None
        return self._database

    @property
    def storage_status(self):
        return self._database_status


class DataBaseProvider(AbstractDataBaseProvider):

    _cached_async_decorators = dict()  # Global for all DbStorageProvider instances

    def __init__(self, config: GeneralConfig):
        self.general_config = config
        self.model_settings = {}

        for model in config.models:
            # TODO: improve model loading
            model_class = locate(model.import_path)

            if not model_class:
                raise MalformedConfigurationError(f"Couldn't import '{model.import_path}'")

            if not issubclass(model_class, CsmModel):
                raise MalformedConfigurationError(f"'{model.import_path}'"
                                                  f" must be a subclass of CsmModel")

            self.model_settings[model_class] = model

    def get_storage(self, model: Type[CsmModel]):
        if model not in self.model_settings:
            raise MalformedConfigurationError(f"No configuration for {model}")

        if model in self._cached_async_decorators:
            return self._cached_async_decorators[model]

        self._cached_async_decorators[model] = AsyncDataBase(model, self.model_settings[model],
                                                             self.general_config)
        return self._cached_async_decorators[model]
