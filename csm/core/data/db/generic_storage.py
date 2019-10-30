#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          generic_storage.py
 _description:      Generic Storage Design

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

from schematics.exceptions import ValidationError, ConversionError

from csm.common.errors import DataAccessInternalError
from csm.core.blogic.models import CsmModel
from csm.core.data.access import IDataBase, Query, IFilterTreeVisitor
from csm.core.data.access import ExtQuery
from csm.core.data.access import IFilter
from csm.core.data.access.filters import (FilterOperationCompare, FilterOperationOr,
                                          FilterOperationAnd)


class GenericDataBase(IDataBase):
    """Generic database class for aggregation functions"""

    _model_scheme = None

    async def store(self, obj: CsmModel):
        """
        Store object into Storage

        :param Model obj: Arbitrary CSM object for storing into DB

        """
        try:
            obj.validate()  # validate that object is correct and perform necessary type conversions
        except ValidationError as e:
            raise DataAccessInternalError(f"{e}")
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

        if self._model_scheme.keys() - obj.fields.keys():
            missing_keys = self._model_scheme.keys() - obj.fields.keys()
            raise DataAccessInternalError(f"Store object doesn't have necessary model properties:"
                                          f"{','.join([k for k in missing_keys])}")
        elif obj.fields.keys() - self._model_scheme.keys():
            extra_keys = obj.fields.keys() - self._model_scheme.keys()
            raise DataAccessInternalError(f"Object to store has new model properties:"
                                          f"{','.join([k for k in extra_keys])}")

    async def get(self, query: Query):
        """
        Get object from Storage by Query

        :param query:
        :return: empty list or list with objects which satisfy the passed query condition
        """
        # Put Generic code here. We can't find it
        pass

    async def delete(self, filter_obj: IFilter):
        """
        Delete objects in DB by Query

        :param IFilter filter_obj: filter object to perform delete operation
        :return: number of deleted entries
        """
        # Put Generic code here. We can't find it
        pass

    async def update(self, query: Query, to_update: dict):
        """
        Update object in Storage by Query

        :param Query query: query object which describes what objects need to update
        :param dict to_update: dictionary with fields and values which should be updated
        """
        # Put Generic code here. We can't find it
        pass

    async def sum(self, ext_query: ExtQuery):
        """
        Sum Aggregation function

        :param ExtQuery ext_query: Extended query which describes how to perform sum aggregation
        :return:
        """
        pass

    async def avg(self, ext_query: ExtQuery):
        """Average Aggregation function

        :param ExtQuery ext_query: Extended query which describes how to perform average
                                   aggregation
        :return:
        """
        pass

    async def count(self, filter_obj: IFilter) -> int:
        """
        Returns count of entities for given filter_obj

        :param filter_obj: filter object to perform count operation
        :return:
        """
        pass

    async def count_by_query(self, ext_query: ExtQuery):
        """
        Count Aggregation function

        :param ExtQuery ext_query: Extended query which describes to perform count aggregation
        :return:
        """
        pass

    async def max(self, ext_query: ExtQuery):
        """
        Max Aggregation function

        :param ExtQuery ext_query: Extended query which describes how to perform Max aggregation
        :return:
        """
        pass

    async def min(self, ext_query: ExtQuery):
        """
        Min Aggregation function

        :param ExtQuery ext_query: Extended query which describes how to perform Min aggregation
        :return:
        """
        pass


class GenericQueryConverter(IFilterTreeVisitor):
    """
    Implementation of filter tree visitor that converts the tree into the Query
    object of elasticsearch-dsl library.

    Usage:
    converter = GenericQueryConverter()
    q_obj = converter.build(filter_root)
    """

    def handle_and(self, entry: FilterOperationAnd):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed AND operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret & operand.accept_visitor(self)

        return ret

    def handle_or(self, entry: FilterOperationOr):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed OR operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret | operand.accept_visitor(self)

        return ret

    def handle_compare(self, entry: FilterOperationCompare):
        # Put Generic code here. We can't find it
        pass
