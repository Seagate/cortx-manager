import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Type, Union

from elasticsearch_dsl import Q, Search
from elasticsearch import Elasticsearch
from elasticsearch import ElasticsearchException, RequestError, ConflictError
from schematics.models import Model
from schematics.types import (StringType, DecimalType, DateType, IntType, BaseType, BooleanType,
                              DateTimeType, UTCDateTimeType, FloatType, LongType, NumberType)
from schematics.exceptions import ConversionError, ValidationError

from csm.common.errors import CsmInternalError
from csm.core.data.access import Query, SortOrder
from csm.core.data.access import ExtQuery
from csm.core.data.db import BaseAbstractStorage
from csm.core.blogic.models.alerts import AlertExample
from csm.core.blogic.models import CsmModel
from csm.common.errors import DataAccessExternalError, DataAccessInternalError
from csm.core.data.access.filters import (IFilterTreeVisitor, FilterOperationAnd,
                                          FilterOperationOr, FilterOperationCompare)
from csm.core.data.access.filters import Compare, And, Or
from csm.core.data.access.filters import ComparisonOperation, IFilterQuery


__all__ = ["ElasticSearchStorage"]


class ESWords:
    """ElasticSearch service words"""

    MAPPINGS = "mappings"
    PROPERTIES = "properties"
    DATA_TYPE = "type"
    ALIASES = "aliases"
    SETTINGS = "settings"
    SOURCE = "_source"
    ASC = "asc"
    DESC = "desc"
    MODE = "mode"
    ORDER = "order"
    COUNT = "count"
    DELETED = "deleted"


# TODO: Add remaining schematics data types
DATA_MAP = {
    StringType: "text",  # TODO: keyword
    IntType: "integer",
    DateType: "date",
    BooleanType: "boolean",
    DateTimeType: "date",
    UTCDateTimeType: "date",
    DecimalType: "keyword",  # TODO: maybe a poor text?
    FloatType: "float",  # TODO: it is possible to increase type to elasticsearch's double
    LongType: "long",
    NumberType: "short",  # TODO: Size of ES's type can be increased to 'integer'
    # DictType: "nested"
}


def field_to_str(field: Union[str, BaseType]) -> str:
    """
    Convert model field to its string representation

    :param Union[str, BaseType] field:
    :return: model field string representation
    """
    if isinstance(field, str):
        return field
    elif isinstance(field, BaseType):
        return field.name
    else:
        raise DataAccessInternalError("Failed to process left side of comparison operation")


class ElasticSearchQueryConverter(IFilterTreeVisitor):
    """
    Implementation of filter tree visitor that converts the tree into the Query
    object of elasticsearch-dsl library.

    Usage:
    converter = ElasticSearchQueryConverter()
    q_obj = converter.build(filter_root)
    """

    def __init__(self, model):
        self.comparison_conversion = {
            ComparisonOperation.OPERATION_EQ: self._match_query,
            ComparisonOperation.OPERATION_LT: self._range_generator('lt'),
            ComparisonOperation.OPERATION_GT: self._range_generator('gt'),
            ComparisonOperation.OPERATION_LEQ: self._range_generator('lte'),
            ComparisonOperation.OPERATION_GEQ: self._range_generator('gte')
        }
        # Needed to perform for type casting if field name is pure string,
        # not of format Model.field
        self._model = model

    @staticmethod
    def _match_query(field: str, target):
        obj = {
            field: target
        }

        return Q("match", **obj)

    @staticmethod
    def _range_generator(op_string: str):
        def _make_query(field: str, target):
            obj = {
                field: {
                    op_string: target
                }
            }

            return Q("range", **obj)

        return _make_query

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

        field_str = field_to_str(field)

        op = entry.get_operation()
        try:
            if isinstance(field, str):
                right_operand = getattr(self._model, field_str).to_native(entry.get_right_operand())
            else:
                right_operand = field.to_native(entry.get_right_operand())
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

        return self.comparison_conversion[op](field_str, right_operand)


class ElasticSearchDataMapper:
    """ElasticSearch data mappings helper"""

    def __init__(self, model: Type[CsmModel]):
        """

        :param Type[CsmModel] model: model for constructing data mapping for index in ElasticSearch
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


class ElasticSearchQueryService:

    """Query service-helper for Elasticsearch"""

    def __init__(self, index: str, es_client: Elasticsearch,
                 query_converter: ElasticSearchQueryConverter):
        self._index = index
        self._es_client = es_client
        self._query_converter = query_converter

    def search_by_query(self, query: Query) -> Search:
        """
        Get Elasticsearch Search instance by given query object

        :param Query query: query object to construct ES's Search object
        :return: Search object constructed by given `query` param
        """
        def convert(name):
            return ESWords.ASC if name == SortOrder.ASC else ESWords.DESC

        extra_params = dict()
        sort_by = dict()
        search = Search(index=self._index, using=self._es_client)

        q = query.data

        if q.filter_by is not None:
            filter_by = self._query_converter.build(q.filter_by)
            search = search.query(filter_by)

        if q.offset is not None:
            extra_params["from_"] = q.offset
        if q.limit is not None:
            extra_params["size"] = q.limit + extra_params.get("from_", 0)

        if any((i is not None for i in (q.offset, q.limit))):
            search = search.extra(**extra_params)

        if q.order_by is not None:
            sort_by[field_to_str(q.order_by.field)] = {ESWords.ORDER: convert(q.order_by.order)}
            search = search.sort(sort_by)

        return search


class ElasticSearchStorage(BaseAbstractStorage):

    """ElasticSearch Storage Interface Implementation"""

    def __init__(self, es_client: Elasticsearch, model: Type[CsmModel], collection: str,
                 thread_pool_exec: ThreadPoolExecutor, loop: asyncio.AbstractEventLoop = None):
        """

        :param Elasticsearch es_client: elasticsearch client
        :param Type[CsmModel] model: model (class object) to associate it with elasticsearch storage
        :param str collection: string represented collection for `model`
        :param ThreadPoolExecutor thread_pool_exec: thread pool executor
        :param BaseEventLoop loop: asyncio event loop
        """
        self._es_client = es_client
        self._tread_pool_exec = thread_pool_exec
        self._loop = loop or asyncio.get_event_loop()
        self._collection = collection

        self._query_converter = ElasticSearchQueryConverter(model)

        # We are associating index name in ElasticSearch with given collection
        self._index = self._collection

        if not isinstance(model, type) or CsmModel not in model.__bases__:
            raise DataAccessInternalError("Model parameter is not a Class object or not inherited "
                                          "from csm.core.blogic.models.CsmModel")
        self._model = model  # Needed to build returning objects

        self._index_info = None
        self._properties = None

        self._query_service = ElasticSearchQueryService(self._index, self._es_client,
                                                        self._query_converter)

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

    async def store(self, obj: CsmModel):
        """
        Store object into Storage

        :param Model obj: Arbitrary CSM object for storing into DB

        """
        def _store(_id, _doc: dict):
            """
            Store particular object into elasticsearch index

            :param dict _doc: dict representation of the object
            :return: elastic search server response
            """
            # TODO: is it needed to use id?
            _result = self._es_client.index(index=self._index, id=_id, body=_doc)
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
            schematic_type = self._model.fields.get(key)
            try:
                doc[key] = schematic_type.validate(getattr(obj, key))  # convert into necessary type
            except ValidationError as e:
                raise DataAccessInternalError(f"Field '{key}' validation error: {e}")
            except ConversionError as e:
                raise DataAccessInternalError(f"Field '{key}' conversion error: {e}")

        obj_id = str(obj.primary_key_val)  # convert primary key value into string

        # TODO: check future for the error and result
        # future = self._tread_pool_exec.submit(_store, doc)
        # result = self._loop.run_until_complete(future)

        result = await self._loop.run_in_executor(self._tread_pool_exec, _store, obj_id, doc)
        # TODO: discuss that. May be better avoid this to increase store performance
        # NOTE: make refresh to ensure that updated results will be available quickly
        await self._refresh_index()
        return result

    async def get(self, query: Query) -> List[Model]:
        """
        Get object from Storage by Query

        :param query:
        :return: empty list or list with objects which satisfy the passed query condition
        """
        def _get(_query):
            search = self._query_service.search_by_query(_query)
            return search.execute()

        result = await self._loop.run_in_executor(self._tread_pool_exec, _get, query)
        return [self._model(hit.to_dict()) for hit in result]

    async def get_by_id(self, obj_id: Union[int, str]) -> Union[Model, None]:
        """
        Simple implementation of get function.
        Important note: in terms of this API 'id' means CsmModel.primary_key reference. If model
        contains 'id' field please use ordinary get call. For example,

            await db(YourCsmModel).get(Query().filter_by(Compare(YourCsmModel.id, "=", obj_id)))

        This API call is equivalent to

            await db(YourCsmModel).get(Query().filter_by(
                                                    Compare(YourCsmModel.primary_key, "=", obj_id)))

        :param Union[int, str] obj_id:
        :return: CsmModel if object was found by its id and None otherwise
        """
        query = Query().filter_by(Compare(self._model.primary_key, "=", str(obj_id)))
        result = await self.get(query)
        if result:
            return result.pop()

        return None

    async def update(self, query: Query, to_update: dict):
        """
        Update object in Storage by Query

        :param Query query: query object which describes what objects need to update
        :param dict to_update: dictionary with fields and values which should be updated

        """
        """TODO: it also should take fields to update"""
        pass

    async def _refresh_index(self):
        """
        Refresh index

        :return:
        """
        def _refresh():
            self._es_client.indices.refresh(index=self._index)

        await self._loop.run_in_executor(self._tread_pool_exec, _refresh)

    async def delete(self, filter_obj: IFilterQuery) -> int:
        """
        Delete objects in DB by Query

        :param IFilterQuery filter_obj: filter object to perform delete operation
        :return: number of deleted entries
        """
        def _delete(_by_filter):
            search = Search(index=self._index, using=self._es_client)
            search = search.query(_by_filter)
            return search.delete()

        filter_by = self._query_converter.build(filter_obj)
        # NOTE: Needed to avoid elasticsearch.ConflictError when we perform delete quickly
        #       after store operation
        await self._refresh_index()
        try:
            # TODO: it is possible to return a number of deleted
            result = await self._loop.run_in_executor(self._tread_pool_exec, _delete, filter_by)
        except ConflictError as e:
            raise DataAccessExternalError(f"{e}")

        return result[ESWords.DELETED]

    async def sum(self, ext_query: ExtQuery):
        """
        Sum Aggregation function

        :param ExtQuery ext_query: Extended query which describes how to perform sum aggregation
        :return:
        """
        pass

    async def avg(self, ext_query: ExtQuery):
        """
        Average Aggregation function

        :param ExtQuery ext_query: Extended query which describes how to perform average
                                   aggregation
        :return:
        """
        pass

    async def count(self, filter_obj: IFilterQuery = None) -> int:
        """
        Returns count of entities for given filter_obj

        :param IFilterQuery filter_obj: filter to perform count aggregation
        :return: count of entries which satisfy the `filter_obj`
        """

        def _count(_body):
            return self._es_client.count(index=self._index, body=_body)

        search = Search(index=self._index, using=self._es_client)
        if filter_obj is not None:
            filter_by = self._query_converter.build(filter_obj)
            search = search.query(filter_by)
        else:
            search = search.query()

        result = await self._loop.run_in_executor(self._tread_pool_exec, _count, search.to_dict())
        return result.get(ESWords.COUNT)

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
