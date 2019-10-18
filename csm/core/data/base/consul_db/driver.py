import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import Union, Type
import asyncio

from consul.aio import Consul
from schematics.models import Model
from schematics.types import StringType, IntType

from csm.core.data.access.storage import IStorage
from csm.core.data.base.db_provider import CachedDatabaseDriver
from csm.core.data.base.consul_db import ConsulStorage


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8500


class ConsulConfiguration(Model):
    """
    Consul KVS configuration model
    """

    host = StringType(required=True, default=DEFAULT_HOST)
    port = IntType(required=True, default=DEFAULT_PORT)
    token = StringType()


class ConsulModelConfiguration(Model):
    """
    Model configuration for Consul Storage
    """

    collection = StringType(required=True)


class ConsulDriver(CachedDatabaseDriver):
    """

    Driver for Consul database
    :param config: Instance of ConsulConfiguration or a dictionary that complies with it

    """

    def __init__(self, config: Union[ConsulConfiguration, dict]):
        super().__init__()

        config = self._convert_config(config, ConsulConfiguration)

        loop = asyncio.get_event_loop()  # TODO: It is possible to put already created loop here

        self.consul_client = Consul(host=config.host, port=config.port, token=config.token,
                                    loop=loop)

    def __del__(self):
        self.consul_client.close()

    async def _create_storage(self, model,
                              config: Union[ConsulModelConfiguration, dict]) -> IStorage:

        # TODO: analyze model and config: it will be required to create new Consul instance
        config = self._convert_config(config, ConsulModelConfiguration)

        # needed to perform tree traversal in non-blocking mode
        pool = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        loop = asyncio.get_event_loop()
        consul_storage = ConsulStorage(self.consul_client, model, config.collection, pool, loop)
        await consul_storage.create_object_root()

        return consul_storage
