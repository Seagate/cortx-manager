from elasticsearch import ElasticSearch
from schematics.models import Model
from schematics.types import StringType, ListType
from typing import Union
from csm.core.blogic.data_access.storage import IStorage
from csm.core.databases.db_provider import CachedDatabaseDriver


class ElasticSearchConfiguration(Model):
    hosts = ListType(StringType, min_size=1)
    login = StringType(default=None)
    password = StringType(default=None)


class ElasticSearchDriver(CachedDatabaseDriver):
    """
    Driver for ElasticSearch database
    :param config: Instance of ElasticSearchConfiguration or a dictionary that complies with it
    """
    def __init__(self, config: Union[ElasticSearchConfiguration, dict]):
        super().__init__()

        if not isinstance(config, ElasticSearchConfiguration):
            config = ElasticSearchConfiguration(config)

        auth = None
        if config.login:
            auth = (config.login, config.password)

        self.elastic_instance = ElasticSearch(hosts=config.hosts, http_auth=auth)

    async def create_storage(self, model) -> IStorage:
        # return ElasticSearchStorage(model, self.elastic_instance)
        pass
