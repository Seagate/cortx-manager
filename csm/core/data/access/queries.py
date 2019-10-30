#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          queries.py
 _description:      Interface for DB queries

 Creation Date:     6/10/2019
 Author:            Alexander Nogikh
                    Dmitry Didenko

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from schematics.types import BaseType

from csm.core.data.access.filters import IFilter
from enum import Enum


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class OrderBy:

    """Class to represent order by parameters for DB"""

    def __init__(self, field, order: SortOrder = SortOrder.ASC):
        self.field = field
        self.order = order


class Query:

    """Storage Query API"""

    class Data:

        """Data storage class for Query parameters"""

        # TODO: it can be a schematics model
        def __init__(self, order_by: OrderBy = None, filter_by: IFilter = None, limit: int = None,
                     offset: int = None):

            self.order_by = order_by
            self.filter_by = filter_by
            self.limit = limit
            self.offset = offset

    def __init__(self, order_by: OrderBy = None, filter_by: IFilter = None, limit: int = None,
                 offset: int = None):

        self.data = self.Data(order_by, filter_by, limit, offset)

    # TODO: order_by can be chained and we can store an array of fields to sort by them
    def order_by(self, by_field: BaseType, by_order: SortOrder = SortOrder.ASC):
        """
        Set Query order_by parameter

        :param BaseType by_field: particular field to perform ordering
        :param int by_order: direction of ordering

        """
        self.data.order_by = OrderBy(by_field, by_order)
        return self

    def filter_by(self, by_filter: IFilter):
        """
        Set Query filter parameter

        :param IFilter by_filter: filter parameter for Query
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

    class Data:

        """Data storage class for Query parameters"""

        # TODO: it can be a schematics model
        def __init__(self, order_by: OrderBy = None, group_by: BaseType = None,
                     filter_by: IFilter = None, limit: int = None, offset: int = None):

            self.order_by = order_by
            self.group_by = group_by
            self.filter_by = filter_by
            self.limit = limit
            self.offset = offset

    def __init__(self):
        super().__init__()

    def group_by(self, by_field: BaseType):
        """
        Set Query group_by parameter

        :param BaseType by_field: field for grouping

        """
        self.data.group_by = by_field
        return self
