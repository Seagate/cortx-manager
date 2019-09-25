from abc import ABC, abstractmethod

from csm.core.data_access.queries import Query
from csm.core.data_access.queries import ExtQuery
from csm.core.blogic.models import Object


class IStorage(ABC):

    """Abstract Storage Interface"""

    @abstractmethod
    async def store(self, obj: Object):
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
            :param dict to_update: dictionary with fields and values whish should be updated

        """
        """TODO: it also should take fields to update"""
        pass

    async def delete(self, query: Query):
        """Delete objects in DB by Query

            :param Query query: query object to perform delete operation

        """
        pass

    async def sum(self, ext_query: ExtQuery):
        """Sum Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform sum aggregation

        """
        pass

    async def avg(self, ext_query: ExtQuery):
        """Average Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform average
                                       aggregation

        """
        pass

    async def count(self, ext_query: ExtQuery):
        """Count Aggregation function

            :param ExtQuery ext_query: Extended query which describes to perform count aggregation

        """
        pass

    async def max(self, ext_query: ExtQuery):
        """Max Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform Max aggregation
        """
        pass

    async def min(self, ext_query: ExtQuery):
        """Min Aggregation function

            :param ExtQuery ext_query: Extended query which describes how to perform Min aggregation

        """
        pass
