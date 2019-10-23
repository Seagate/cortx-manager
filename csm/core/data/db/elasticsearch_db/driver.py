import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import Union, Type
import asyncio

from elasticsearch import Elasticsearch
from schematics.models import Model
from schematics.types import StringType, ListType
from schematics.exceptions import BaseError

from csm.core.data.access.storage import IStorage
from csm.core.data.base.db_provider import CachedDatabaseDriver
from csm.common.errors import MalformedConfigurationError
from csm.core.data.base.elasticsearch_db import ElasticSearchStorage


class ElasticSearchConfiguration(Model):
    """
    Configuration for ElasticSearch
    """

    hosts = ListType(StringType, min_size=1)
    login = StringType(default=None)
    password = StringType(default=None)
    # TODO: looks that port is also necessary


class ElasticSearchModelConfiguration(Model):
    """
    Model configuration for ElasticSearch storage
    """

    index = StringType(required=True)


class ElasticSearchDriver(CachedDatabaseDriver):
    """
    Driver for ElasticSearch database
    :param config: Instance of ElasticSearchConfiguration or a dictionary that complies with it
    """

    def __init__(self, config: Union[ElasticSearchConfiguration, dict]):
        super().__init__()

        config = self._convert_config(config, ElasticSearchConfiguration)

        auth = None
        if config.login:
            auth = (config.login, config.password)

        self.elastic_instance = Elasticsearch(hosts=config.hosts, http_auth=auth)

    async def _create_storage(self, model,
                              config: Union[ElasticSearchModelConfiguration, dict]) -> IStorage:

        # TODO: analyze model and config: it will be required to create new ElasticSearch instance
        config = self._convert_config(config, ElasticSearchModelConfiguration)

        pool = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        loop = asyncio.get_event_loop()
        es_storage = ElasticSearchStorage(self.elastic_instance, model, config.index, pool, loop)
        await es_storage.attach_to_index()

        return es_storage
