import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Type

from elasticsearch_dsl import Q, Search
from elasticsearch import Elasticsearch
from elasticsearch import ElasticsearchException, RequestError
from schematics.models import Model
from schematics.models import FieldDescriptor
from schematics.types import StringType, DecimalType, DateType, IntType, BaseType

from csm.common.errors import CsmInternalError
from csm.core.blogic.data_access import Query
from csm.core.blogic.data_access import ExtQuery
from csm.core.databases import BaseAbstractStorage
from csm.core.blogic.models import Alert
from csm.core.blogic.models import CsmModel
from csm.core.blogic.data_access import DataAccessExternalError, DataAccessInternalError
from csm.core.blogic.data_access.filters import (IFilterTreeVisitor, FilterOperationAnd,
                                                 FilterOperationOr, FilterOperationCompare)
from csm.core.blogic.data_access.filters import Compare, And, Or
from csm.core.blogic.data_access.filters import ComparisonOperation, IFilterQuery


class ESWords:

    """ElasticSearch service words"""

    MAPPINGS = "mappings"
    PROPERTIES = "properties"
    DATA_TYPE = "type"
    ALIASES = "aliases"
    SETTINGS = "settings"
    SOURCE = "_source"


# TODO: Add remaining schematics data types
DATA_MAP = {
    StringType: "text",  # TODO: keyword
    IntType: "integer",
    DateType: "date"
}


def _match_query(field: str, target):
    obj = {
        field: target
    }

    return Q("match", **obj)


def _range_generator(op_string: str):
    def _make_query(field: str, target):
        obj = {
            field: {
                op_string: target
            }
        }

        return Q("range", **obj)

    return _make_query


class ElasticSearchQueryConverter(IFilterTreeVisitor):
    """
    Implementation of filter tree visitor that converts the tree into the Query
    object of elasticsearch-dsl library.

    Usage:
    converter = ElasticSearchQueryConverter()
    q_obj = converter.build(filter_root)
    """
    def __init__(self):
        self.comparison_conversion = {
            ComparisonOperation.OPERATION_EQ: _match_query,
            ComparisonOperation.OPERATION_LT: _range_generator('lt'),
            ComparisonOperation.OPERATION_GT: _range_generator('gt'),
            ComparisonOperation.OPERATION_LEQ: _range_generator('lte'),
            ComparisonOperation.OPERATION_GEQ: _range_generator('gte')
        }

    def build(self, root: IFilterQuery):
        # TODO: may be, we should move this method to the entity that processes
        # Query objects
        return root.accept_visitor(self)

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
        field = entry.get_left_operand()

        if isinstance(field, str):
            field_str = field
        elif isinstance(field, BaseType):
            field_str = field.name
        else:
            raise Exception("Failed to process left side of comparison operation")

        op = entry.get_operation()
        return self.comparison_conversion[op](field_str, entry.get_right_operand())


class ElasticSearchDataMapper:

    """ElasticSearch data mappings helper"""

    def __init__(self, model: Type[Model]):
        """

        :param Type[Model] model: model for constructing data mapping for index in ElasticSearch
        """
        self._model = model
        self._mapping = {
            ESWords.MAPPINGS: {
                ESWords.PROPERTIES: {
                }
            }
        }

    def _add_property(self, name: str, property_type: Type[BaseType]):
        """
        Add property to mappings

        :param str name: property name
        :param Type[BaseType] property_type: type of property for given property `name`
        :return:
        """
        properties = self._mapping[ESWords.MAPPINGS][ESWords.PROPERTIES]

        if name in properties:
            raise CsmInternalError(f"Repeated property name in model: {name}")

        properties[name] = dict()
        properties[name][ESWords.DATA_TYPE] = DATA_MAP[property_type]
        # properties[name]["index"] = "false"

    def build_index_mappings(self) -> dict:
        """
        Build ElasticSearch index data mapping

        :return: elasticsearch data mappings dict
        """
        for name, property_type in self._model.fields.items():
            self._add_property(name, type(property_type))

        return self._mapping


class ElasticSearchStorage(BaseAbstractStorage):

    """ElasticSearch Storage Interface Implementation"""

    def __init__(self, es_client: Elasticsearch, model: Type[Model], collection: str,
                 thread_pool_exec: ThreadPoolExecutor, loop: asyncio.AbstractEventLoop = None):
        """

        :param Elasticsearch es_client: elasticsearch client
        :param Type[Model] model: model (class object) to associate it with elasticsearch storage
        :param str collection: string represented collection for `model`
        :param ThreadPoolExecutor thread_pool_exec: thread pool executor
        :param BaseEventLoop loop: asyncio event loop
        """
        self._es_client = es_client
        self._tread_pool_exec = thread_pool_exec
        self._loop = asyncio.get_running_loop() if loop is None else loop
        self._collection = collection

        self._query_converter = ElasticSearchQueryConverter()

        # We are associating index name in ElasticSearch with given collection
        self._index = self._collection

        if not isinstance(model, type) or CsmModel not in model.__bases__:
            raise DataAccessInternalError("model parameter is not a Class object or not inherited "
                                          "from schematics.Model")
        self._model = model  # Needed to build returning objects

        self._index_info = None
        self._properties = None

    async def attach_to_index(self) -> None:
        """
        Provides async method to connect storage to index bound to provided model and collection
        :return:
        """
        def _get_alias(_index):
            return self._es_client.indices.get_alias(self._index, ignore_unavailable=True)

        def _create(_index, _body):
            self._es_client.indices.create(index=_index, body=_body)

        def _get(_index):
            return self._es_client.indices.get(self._index)

        indices = await self._loop.run_in_executor(self._tread_pool_exec, _get_alias, self._index)
        # self._obj_index = self._es_client.indices.get_alias("*")
        if indices.get(self._index, None) is None:
            data_mappings = ElasticSearchDataMapper(self._model)
            mappings_dict = data_mappings.build_index_mappings()
            # self._es_client.indices.create(index=model.__name__, ignore=400, body=mappings_dict)
            await self._loop.run_in_executor(self._tread_pool_exec,
                                             _create, self._index, mappings_dict)

        self._index_info = await self._loop.run_in_executor(self._tread_pool_exec,
                                                            _get, self._index)
        self._properties = self._index_info[self._index][ESWords.MAPPINGS][ESWords.PROPERTIES]

    # TODO: rename to CsmModel
    async def store(self, obj: Model):
        """
        Store object into Storage

        :param Model obj: Arbitrary CSM object for storing into DB

        """
        def _store(_doc: dict):
            """
            Store particular object into elasticsearch index

            :param dict _doc: dict representation of the object
            :return: elastic search server response
            """
            # TODO: is it needed to use id?
            _result = self._es_client.index(index=self._index, id=obj.id, body=_doc)
            return _result

        doc = dict()
        if self._properties.keys() - obj.fields.keys():
            missing_keys = self._properties.keys() - obj.fields.keys()
            raise DataAccessInternalError(f"Store object doesn't have necessary model properties:"
                                          f"{','.join([k for k in missing_keys])}")
        elif obj.fields.keys() - self._properties.keys():
            extra_keys = obj.fields.keys() - self._properties.keys()
            raise DataAccessInternalError(f"Object to store has new model properties:"
                                          f"{','.join([k for k in extra_keys])}")

        for key in self._properties:
            doc[key] = getattr(obj, key)

        # TODO: check future for the error and result
        # future = self._tread_pool_exec.submit(_store, doc)
        # result = self._loop.run_until_complete(future)

        result = await self._loop.run_in_executor(self._tread_pool_exec, _store, doc)
        return result

    async def get(self, query: Query) -> List[Model]:
        """
        Get object from Storage by Query

        :param query:
        :return: empty list or list with objects which satisfy the passed query condition
        """
        def _get(_q_obj):
            search = Search(index="alert", using=self._es_client)
            search = search.query(_q_obj)
            return search.execute()

        q_obj = self._query_converter.build(query.data.filter_by)
        result = await self._loop.run_in_executor(self._tread_pool_exec, _get, q_obj)
        return [self._model(hit.to_dict()) for hit in result]

    async def get_by_id(self, obj_id: int) -> Model:
        """
        Simple implementation of get function

        :param int obj_id:
        :return:
        """
        def _get(_id: int):
            """
            Simple get object function by its id
            :param int _id: object id to get
            :return: elasticsearch server response
            """
            _result = self._es_client.get(index=self._index, id=_id)
            return _result

        result = await self._loop.run_in_executor(self._tread_pool_exec, _get, obj_id)
        data = result[ESWords.SOURCE]

        return self._model(data)

    async def update(self, query: Query, to_update: dict):
        """Update object in Storage by Query

            :param Query query: query object which describes what objects need to update
            :param dict to_update: dictionary with fields and values which should be updated

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
