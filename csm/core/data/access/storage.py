from abc import ABC, abstractmethod
from typing import Type, Union
from csm.core.blogic.data_access import Query
from csm.core.blogic.data_access import ExtQuery
from csm.core.blogic.data_access import IFilterQuery
from csm.core.blogic.models import CsmModel


class IStorage(ABC):

    """Abstract Storage Interface"""

    @abstractmethod
    async def store(self, obj: CsmModel):
        """Store object into Storage

            :param Object obj: Arbitrary CSM object for storing into DB

        """
        pass

    @abstractmethod
    async def get(self, query: Query):
        """Get object from Storage by Query

            :param Query query: query object which describes request to Storage

        """
        pass

    @abstractmethod
    async def update(self, query: Query, to_update: dict):
        """Update object in Storage by Query

            :param Query query: query object which describes what objects need to update
            :param dict to_update: dictionary with fields and values which should be updated

        """
        """TODO: it also should take fields to update"""
        pass

    @abstractmethod
    async def delete(self, filter_obj: IFilterQuery):
        """Delete objects in DB by Query

            :param IFilterQuery filter_obj: filter object to perform delete operation

        """
        pass

    @abstractmethod
    async def sum(self, ext_query: ExtQuery):
        """Sum Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform sum aggregation

        """
        pass

    @abstractmethod
    async def avg(self, ext_query: ExtQuery):
        """Average Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform average
                                       aggregation

        """
        pass

    @abstractmethod
    async def count(self, ext_query: ExtQuery = None):
        """Count Aggregation function

            :param ExtQuery ext_query: Extended query which describes to perform count aggregation

        """
        pass

    @abstractmethod
    async def max(self, ext_query: ExtQuery):
        """Max Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform Max aggregation

        """
        pass

    @abstractmethod
    async def min(self, ext_query: ExtQuery):
        """Min Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform Min aggregation

        """
        pass


class AbstractDbProvider(ABC):
    """
    A class for data storage access.

    Below you can see its intended usage.
    Suppose db is an instance of AbstractDbProvider.

    await db(SomeModel).get(some_query)
    await db(some_model_instance).get(some_query)  # we can avoid passing model class

    """
    def __call__(self, model: Union[CsmModel, Type[CsmModel]]) -> IStorage:
        if isinstance(model, CsmModel):
            model = type(model)

        return self.get_storage(model)

    @abstractmethod
    def get_storage(self, model: Type[CsmModel]) -> IStorage:
        pass
