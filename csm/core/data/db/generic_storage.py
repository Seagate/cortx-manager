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
from typing import Any, Union

from schematics.exceptions import ValidationError, ConversionError

from csm.common.errors import DataAccessInternalError
from csm.core.blogic.models import CsmModel
from csm.core.data.access import IDataBase, Query, IFilterTreeVisitor
from csm.core.data.access import ExtQuery
from csm.core.data.access import IFilter
from csm.core.data.access.filters import (FilterOperationCompare, FilterOperationOr,
                                          FilterOperationAnd, Compare)


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

    async def get_by_id(self, obj_id: Any) -> Union[CsmModel, None]:
        """
        Simple implementation of get function.
        Important note: in terms of this API 'id' means CsmModel.primary_key reference. If model
        contains 'id' field please use ordinary get call. For example,

            await db(YourCsmModel).get(Query().filter_by(Compare(YourCsmModel.id, "=", obj_id)))

        This API call is equivalent to

            await db(YourCsmModel).get(Query().filter_by(
                                                    Compare(YourCsmModel.primary_key, "=", obj_id)))

        :param Any obj_id:
        :return: CsmModel if object was found by its id and None otherwise
        """
        id_field = getattr(self._model, self._model.primary_key)
        try:
            converted = id_field.to_native(obj_id)
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

        query = Query().filter_by(Compare(self._model.primary_key, "=", converted))

        result = await self.get(query)

        if result:
            return result.pop()

        return None

    async def delete(self, filter_obj: IFilter):
        """
        Delete objects in DB by Query

        :param IFilter filter_obj: filter object to perform delete operation
        :return: number of deleted entries
        """
        # Put Generic code here. We can't find it
        pass

    async def update(self, filter_obj: IFilter, to_update: dict) -> int:
        """
        Update object in Storage by filter

        :param IFilter filter_obj: filter which specifies what objects need to update
        :param dict to_update: dictionary with fields and values which should be updated
        :return: number of entries updated
        """
        # Generic code for update method of particular storage
        unnecessary_fields = set(to_update.keys()) - set(self._model_scheme.keys())
        if unnecessary_fields:
            raise DataAccessInternalError(f"to_update dictionary contains fields which are not "
                                          f"presented in model:{unnecessary_fields}")

        try:
            for key in to_update:
                to_update[key] = getattr(self._model, key).to_native(to_update[key])
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

    async def update_by_id(self, obj_id: Any, to_update: dict) -> None:
        """
        Update csm model in db by id (primary key)

        :param Any obj_id: id-value of the object which should be updated (primary key value)
        :param dict to_update: dictionary with fields and values which should be updated
        :return:
        """
        # Generic code for update_by_id method of particular method
        id_field = getattr(self._model, self._model.primary_key)
        try:
            converted = id_field.to_native(obj_id)
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

        filter = Compare(self._model.primary_key, "=", converted)

        await self.update(filter, to_update)

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

    async def count(self, filter_obj: IFilter = None) -> int:
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
