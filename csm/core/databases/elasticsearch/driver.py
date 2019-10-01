from elasticsearch import ElasticSearch
from schematics.models import Model
from schematics.types import StringType, ListType
from schematics.exceptions import BaseError
from typing import Union
from csm.core.blogic.data_access.storage import IStorage
from csm.core.databases.db_provider import CachedDatabaseDriver
from csm.core.blogic.data_access.errors import MalformedConfigurationError


class ElasticSearchConfiguration(Model):
    hosts = ListType(StringType, min_size=1)
    login = StringType(default=None)
    password = StringType(default=None)


class ElasticSearchModelConfiguration(Model):
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

        self.elastic_instance = ElasticSearch(hosts=config.hosts, http_auth=auth)

    def _convert_config(self, config: Union[Model, dict], target_model: Type[Model]):
        if isinstance(config, target_model):
            return config

        if isinstance(config, dict):
            try:
                return ElasticSearchModelConfiguration(config)
            except BaseError:
                raise MalformedConfigurationError("Invalid ElasticSearch configuration")

        raise MalformedConfigurationError("Invalid ElasticSearch configuration: "
                                            "unexpected type")

    async def create_storage(self, model,
                    config: Union[ElasticSearchModelConfiguration, dict]) -> IStorage:

        config = self._convert_config(config, ElasticSearchModelConfiguration)

        # return ElasticSearchStorage(model, self.elastic_instance)
        pass
