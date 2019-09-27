
from csm.core.blogic.data_access import IStorage
from csm.core.blogic.data_access import ExtQuery


class BaseAbstractStorage(IStorage):

    """Base Abstract Storage class for aggregation functions"""

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
