import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from elasticsearch_dsl import Q
from elasticsearch import Elasticsearch
from elasticsearch import ElasticsearchException, RequestError
from schematics.models import Model
from schematics.models import FieldDescriptor
from schematics.types import StringType, DecimalType, DateType, IntType

from csm.common.errors import CsmInternalError
from csm.core.blogic.data_access import Query
from csm.core.blogic.data_access import ExtQuery
from csm.core.databases import BaseAbstractStorage
from csm.core.blogic.models import Alert
from csm.core.blogic.data_access import DataAccessExternalError, DataAccessInternalError
from csm.core.blogic.filters import (IFilterTreeVisitor, FilterOperationAnd,
                                     FilterOperationOr, FilterOperationCompare)
from csm.core.blogic.filters import ComparisonOperation, IFilterQuery


# elasticsearch service words
MAPPINGS = "mappings"
PROPERTIES = "properties"
DATA_TYPE = "type"
ALIASES = "aliases"
SETTINGS = "settings"


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
            ComparisonOperation.OPERATION_LTE: _range_generator('lte'),
            ComparisonOperation.OPERATION_GTE: _range_generator('gte')
        }

    def build(self, root: IFilterQuery):
        # TODO: may be, we should move this method to the entity that processes
        # Query objects
        return self.accept_visitor(root)

    def handle_and(self, entry: FilterOperationAnd):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed AND operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret & operand.accept_visitor(operand)

        return ret

    def handle_or(self, entry: FilterOperationOr):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed OR operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret | operand.accept_visitor(operand)

        return ret

    def handle_compare(self, entry: FilterOperationCompare):
        field = entry.get_left_operand()
        field_str = None

        if isinstance(field, str):
            field_str = field
        elif isinstance(field, FieldDescriptor):
            field_str = field.name
        else:
            raise Exception("Failed to process left side of comparison operation")

        op = entry.get_operation()
        return self.comparison_conversion[op](field_str, entry.get_right_operand())


class ElasticSearchDataMapper:

    """ElasticSearch data mappings helper"""

    def __init__(self, model: Model):
        """

        :param Model model: model for constructing data mapping for index in ElasticSearch
        """
        self._model = model
        self._mapping = {
            MAPPINGS: {
                PROPERTIES: {
                }
            }
        }

    def _add_property(self, name: str, property_type):
        """
        Add property to mappings
        #TODO: add type for property_type
        :param str name: property name
        :param property_type:
        :return:
        """
        properties = self._mapping[MAPPINGS][PROPERTIES]

        if name in properties:
            raise CsmInternalError(f"Repeated property name in model: {name}")

        properties[name] = dict()
        properties[name][DATA_TYPE] = DATA_MAP[property_type]

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

    def __init__(self, es_client: Elasticsearch, model: Model, thread_pool_exec: ThreadPoolExecutor,
                 loop: asyncio.AbstractEventLoop = None):
        """

        :param Elasticsearch es_client: elasticsearch client
        :param Model model: model to associate it with elasticsearch storage
        :param ThreadPoolExecutor thread_pool_exec: thread pool executor
        :param BaseEventLoop loop: asyncio event loop
        """
        self._tread_pool_exec = thread_pool_exec
        self._es_client = es_client
        self._loop = asyncio.get_running_loop() if loop is None else loop

        # We are associating index name in ElasticSearch with model name
        self._index = model.__name__.lower()

        # return a dict object
        # index_data = self._es_client.indices.get(self._index, ignore_unavailable=True)

        indices = self._es_client.indices.get_alias(self._index, ignore_unavailable=True)
        # self._obj_index = self._es_client.indices.get_alias("*")
        if indices.get(self._index, None) is None:
            data_mappings = ElasticSearchDataMapper(model)
            mappings_dict = data_mappings.build_index_mappings()
            # self._es_client.indices.create(index=model.__name__, ignore=400, body=mappings_dict)
            self._es_client.indices.create(index=self._index, body=mappings_dict)

        self._index_info = self._es_client.indices.get(self._index)
        self._properties = self._index_info[self._index][MAPPINGS][PROPERTIES]

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
            # TODO: need to use id?
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

    async def get(self, query: Query):
        """Get object from Storage by Query

            :param Query query: query object which describes request to Storage

        """
        pass

    async def get_by_id(self, obj_id: int):
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
        return result

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


# NOTE: code below for testing purposes. Will be removed

async def store_alert(storage, alert):
    tasks = [asyncio.ensure_future(storage.store(alert))]
    done, pending = await asyncio.wait(tasks)


async def get_alert(storage, query):
    tasks = [asyncio.ensure_future(storage.get(query))]
    done, pending = await asyncio.wait(tasks)


async def get_alert_by_id(storage, id):
    tasks = [asyncio.ensure_future(storage.get_by_id(id))]
    done, pending = await asyncio.wait(tasks)
    for task in done:
        print(task.result())


if __name__ == "__main__":
    pool = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
    loop = asyncio.get_event_loop()
    es = Elasticsearch()
    storage = ElasticSearchStorage(es, Alert, pool, loop)
    _alert = {'id': 1,
              'alert_uuid': 1,
              'status': "Success",
              'type': "Hardware",
              'enclosure_id': 1,
              'module_name': "SSPL",
              'description': "Some Description",
              'health': "Good",
              'health_recommendation': "Replace Disk",
              'location': "USA",
              'resolved': 0,
              'acknowledged': 0,
              'severity': 1,
              'state': "Unknown",
              'extended_info': "No",
              'module_type': "FAN",
              'updated_time': datetime.now(),
              'created_time': datetime.now()
              }
    alert = Alert(_alert)
    loop.run_until_complete(store_alert(storage, alert))
    # query = Query().filter_by(Compare(Alert.id, "=", alert.id))
    # loop.run_until_complete(get_alert(storage, query))
    loop.run_until_complete(get_alert_by_id(storage, alert.id))
    loop.close()
