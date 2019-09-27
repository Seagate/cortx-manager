from schematics.types import BaseType

from csm.core.blogic.data_access.filters import IFilterQuery


ASC = "asc"  # Ascending
DESC = "desc"  # Descending


class OrderBy:

    """Class to represent order by parameters for DB"""

    def __init__(self, field, order: int = ASC):
        self.field = field
        self.order = order


class Query:

    """Storage Query API"""

    class Data:

        """Data storage class for Query parameters"""

        def __init__(self, order_by: OrderBy = None, group_by: BaseType = None,
                     filter_by: IFilterQuery = None, limit: int = None, offset: int = None):

            self.order_by = order_by
            self.group_by = group_by
            self.filter_by = filter_by
            self.limit = limit
            self.offset = offset

    def __init__(self, order_by: OrderBy = None, group_by: BaseType = None,
                 filter_by: IFilterQuery = None, limit: int = None, offset: int = None):

        self.data = self.Data(order_by, group_by, filter_by, limit, offset)

    def order_by(self, by_field: BaseType, by_order: int = ASC):
        """
        Set Query order_by parameter

        :param BaseType by_field: particular field to perform ordering
        :param int by_order: direction of ordering

        """
        self.data.order_by = OrderBy(by_field, by_order)

    def group_by(self, by_field: BaseType):
        """
        Set Query group_by parameter

        :param BaseType by_field: field for grouping

        """
        self.data.group_by = by_field
        return self

    def filter_by(self, by_filter: IFilterQuery):
        """
        Set Query filter parameter

        :param IFilterQuery by_filter: filter parameter for Query
        :return:
        """
        self.data.filter_by = by_filter
        return self

    def limit(self, limit: int):
        """
        Set Query limit parameter

        :param int limit: limit for Query operation
        :return:

        """
        self.data.limit = limit
        return self

    def offset(self, offset: int):
        """
        Set Query offset parameter

        :param int offset: offset for Query
        :return:
        """
        self.data.offset = offset
        return self

    # TODO: having functionality


class ExtQuery(Query):

    """Storage Extended Query API used by Storage aggregation functions"""

    def __init__(self):
        super().__init__()
