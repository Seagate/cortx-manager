import asyncio
from concurrent.futures import ThreadPoolExecutor
from string import Template
from typing import List, Type, Union, Dict
from datetime import datetime
import json
import operator

from consul.aio import Consul
from schematics.models import Model
from schematics.types import BaseType
from schematics.exceptions import ConversionError, ValidationError

from csm.core.data.access import Query, SortOrder
from csm.core.data.access import ExtQuery
from csm.core.data.base import BaseAbstractStorage
from csm.core.blogic.models import CsmModel
from csm.common.errors import DataAccessExternalError, DataAccessInternalError
from csm.core.data.access.filters import (IFilterTreeVisitor, FilterOperationAnd,
                                          FilterOperationOr, FilterOperationCompare)
from csm.core.data.access.filters import ComparisonOperation, IFilterQuery


CONSUL_ROOT = "eos/csm"
OBJECT_DIR = "obj"
PROPERTY_DIR = "prop"


class ConsulWords:

    """Consul service words"""

    VALUE = "Value"
    KEY = "Key"


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


class ConsulQueryConverterWithData(IFilterTreeVisitor):
    """
    Implementation of filter tree visitor which performs query tree traversal in parallel with
    data filtering based on given filter logical and comparison operations

    Usage:
    converter = ConsulQueryConverter()
    q_obj = converter.build(filter_root)
    """

    def __init__(self, model):
        # Needed to perform for type casting if field name is pure string,
        # not of format Model.field
        self._model = model
        self._operator = {
            ComparisonOperation.OPERATION_EQ: operator.eq,
            ComparisonOperation.OPERATION_NE: operator.ne,
            ComparisonOperation.OPERATION_GEQ: operator.ge,
            ComparisonOperation.OPERATION_LEQ: operator.le,
            ComparisonOperation.OPERATION_GT: operator.gt,
            ComparisonOperation.OPERATION_LT: operator.lt
        }
        self._raw_data = None
        self._object_data = None

    def _filter(self, suitable_keys: List[str]):
        return filter(lambda x: x[ConsulWords.KEY] in suitable_keys, self._raw_data)

    def build(self, root: IFilterQuery, raw_data: List[Dict]):
        # TODO: may be, we should move this method to the entity that processes
        # Query objects
        self._raw_data = raw_data
        self._object_data = {
            entry[ConsulWords.KEY]: self._model(json.loads(entry[ConsulWords.VALUE])) for entry in
            self._raw_data}
        return self._filter(root.accept_visitor(self))

    def handle_and(self, entry: FilterOperationAnd):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed AND operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret & operand.accept_visitor(self)  # Operation between python's sets

        return ret

    def handle_or(self, entry: FilterOperationOr):
        operands = entry.get_operands()
        if len(operands) < 2:
            raise Exception("Malformed OR operation: fewer than two arguments")

        ret = operands[0].accept_visitor(self)
        for operand in operands[1:]:
            ret = ret | operand.accept_visitor(self)  # Operation between python's sets

        return ret

    def handle_compare(self, entry: FilterOperationCompare):
        field = entry.get_left_operand()

        field_str = field_to_str(field)

        op = entry.get_operation()
        try:
            right_operand = getattr(self._model, field_str).to_native(entry.get_right_operand())
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

        return set(entry_key for entry_key in
                   filter(lambda x: self._operator[op](getattr(self._object_data[x], field_str),
                                                       right_operand),
                          self._object_data.keys()))


def query_converter_build(model: CsmModel, filter_obj: IFilterQuery, raw_data: List[Dict]):
    query_converter = ConsulQueryConverterWithData(model)
    return query_converter.build(filter_obj, raw_data)


class ConsulKeyTemplate:

    """Class-helper for storing consul key structure"""
    
    _OBJECT_ROOT = f"{CONSUL_ROOT}/$OBJECT_TYPE"
    _OBJECT_DIR = _OBJECT_ROOT + f"/{OBJECT_DIR}"
    _OBJECT_PATH = _OBJECT_DIR + "/$OBJECT_UUID"
    _PROPERTY_DIR = _OBJECT_ROOT + f"/{PROPERTY_DIR}/$PROPERTY_NAME/$PROPERTY_VALUE"
    
    def __init__(self):
        self._object_root = Template(self._OBJECT_ROOT)
        self._object_dir = Template(self._OBJECT_DIR)
        self._object_path = Template(self._OBJECT_PATH)
        self._property_dir = Template(self._PROPERTY_DIR)
        self._object_type_is_set = False

    def set_object_type(self, object_type: str) -> None:
        """
        Render templates using given object_type

        :param str object_type: CsmModel type or collection
        :return:
        """
        self._object_root = Template(self._object_root.substitute(OBJECT_TYPE=object_type))
        self._object_dir = Template(self._object_dir.substitute(OBJECT_TYPE=object_type))
        self._object_path = Template(self._object_path.safe_substitute(OBJECT_TYPE=object_type))
        self._property_dir = Template(self._property_dir.safe_substitute(OBJECT_TYPE=object_type))
        self._object_type_is_set = True

    def _render_template(self, template: Union[Template, str], object_type: str = None, **kwargs):
        if not self._object_type_is_set and object_type is None:
            raise DataAccessInternalError("Need to set object type")
        elif object_type is not None:
            template.substitute(OBJECT_TYPE=object_type, **kwargs)

        return template.substitute(**kwargs)

    def get_object_root(self, object_type: str = None):
        return self._render_template(self._object_root, object_type=object_type)

    def get_object_dir(self, object_type: str = None):
        return self._render_template(self._object_dir, object_type=object_type)

    def get_object_path(self, object_uuid: str, object_type: str = None):
        return self._render_template(self._object_path, object_type=object_type,
                                     OBJECT_UUID=object_uuid)

    def get_property_dir(self, property_name: str, property_value: str, object_type: str = None):
        return self._render_template(self._property_dir, object_type=object_type,
                                     PROPERTY_NAME=property_name,
                                     PROPERTY_VALUE=property_value)


class ConsulStorage(BaseAbstractStorage):
    """Consul Storage Interface Implementation"""

    def __init__(self, consul_client: Consul, model: Type[CsmModel], collection: str,
                 process_pool: ThreadPoolExecutor, loop: asyncio.AbstractEventLoop = None):
        """

        :param Consul consul_client: consul client
        :param Type[CsmModel] model: model (class object) to associate it with consul storage
        :param str collection: string represented collection for `model`
        :param ThreadPoolExecutor process_pool: thread pool executor
        :param AbstractEventLoop loop: asyncio event loop
        """
        self._consul_client = consul_client
        self._collection = collection.lower()

        self._query_converter = ConsulQueryConverterWithData(model)

        # We are associating index name in Consul with given collection
        self._collection = self._collection

        if not isinstance(model, type) or CsmModel not in model.__bases__:
            raise DataAccessInternalError("Model parameter is not a Class object or not inherited "
                                          "from csm.core.blogic.models.CsmModel")
        self._model = model  # Needed to build returning objects

        # self._query_service = ConsulQueryService(self._collection, self._consul_client,
        #                                          self._query_converter)

        # TODO: there is problems with process pool switched to thread pool
        self._process_pool = process_pool
        self._loop = loop

        self._templates = ConsulKeyTemplate()
        self._templates.set_object_type(self._collection)

    async def create_object_root(self) -> None:
        """
        Provides async method to initialize key structure for given object type

        :return:
        """

        obj_root = self._templates.get_object_root()
        index, data = await self._consul_client.kv.get(obj_root)
        if data is None:
            # maybe need to post creation time
            creation_time = datetime.now()
            response = await self._consul_client.kv.put(obj_root, str(creation_time))
            if not response:
                raise DataAccessExternalError(f"Can't put key={obj_root} and "
                                              f"value={str(creation_time)}")

    async def store(self, obj: CsmModel):
        """
        Store object into Storage

        :param Model obj: Arbitrary CSM object for storing into DB

        """
        obj_path = self._templates.get_object_path(obj.primary_key_val)
        obj_path = obj_path.lower()

        try:
            obj.validate()  # validate that object is correct and perform necessary type conversions
        except ValidationError as e:
            raise DataAccessInternalError(f"{e}")
        except ConversionError as e:
            raise DataAccessInternalError(f"{e}")

        obj_val = json.dumps(obj.to_primitive())
        response = await self._consul_client.kv.put(obj_path, obj_val)
        if not response:
            raise DataAccessExternalError(f"Can't put key={obj_path} and value={obj_val}")

    async def _get_all_raw(self) -> Union[None, List[Dict]]:
        obj_dir = self._templates.get_object_dir()
        obj_dir = obj_dir.lower()
        index, data = await self._consul_client.kv.get(obj_dir, recurse=True, consistency=True)
        if data is None:
            return None
        return data

    async def get(self, query: Query) -> List[CsmModel]:
        """
        Get object from Storage by Query

        :param query:
        :return: empty list or list with objects which satisfy the passed query condition
        """
        if query.data.filter_by is None:
            raise DataAccessInternalError("Only filter_by query parameter is now supported")

        raw_data = await self._get_all_raw()

        # NOTE: use processes for parallel data calculations and make true asynchronous work
        suitable_models = await self._loop.run_in_executor(self._process_pool,
                                                           query_converter_build,
                                                           self._model,
                                                           query.data.filter_by,
                                                           raw_data)
        return [self._model(json.loads(entry[ConsulWords.VALUE])) for entry in suitable_models]

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
        obj_path = self._templates.get_object_path(str(obj_id))
        obj_path = obj_path.lower()
        index, data = await self._consul_client.kv.get(obj_path, consistency=True)
        if data is None:
            return None

        return self._model(json.loads(data[ConsulWords.VALUE]))

    async def update(self, query: Query, to_update: dict):
        """
        Update object in Storage by Query

        :param Query query: query object which describes what objects need to update
        :param dict to_update: dictionary with fields and values which should be updated

        """
        """TODO: it also should take fields to update"""
        pass

    async def delete(self, filter_obj: IFilterQuery) -> int:
        """
        Delete objects in DB by Query

        :param IFilterQuery filter_obj: filter object to perform delete operation
        :return: number of deleted entries
        """
        raw_data = await self._get_all_raw()

        # NOTE: use processes for parallel data calculations and make true asynchronous work
        suitable_models = await self._loop.run_in_executor(self._process_pool,
                                                           query_converter_build,
                                                           self._model,
                                                           filter_obj,
                                                           raw_data)
        suitable_models = list(suitable_models)
        tasks = [asyncio.ensure_future(self._consul_client.kv.delete(model[ConsulWords.KEY])) for
                 model in suitable_models]

        done, pending = await asyncio.wait(tasks)

        for task in done:
            if not task.result():
                raise DataAccessInternalError(f"Error happens during object deleting")

        return len(suitable_models)

    async def delete_by_id(self, obj_id: Union[int, str]) -> None:
        obj_path = self._templates.get_object_path(str(obj_id))
        obj_path = obj_path.lower()
        response = await self._consul_client.kv.delete(obj_path)
        if not response:
            raise DataAccessExternalError(f"Error happens during object deleting with id={obj_id}")

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
        raw_data = await self._get_all_raw()
        if filter_obj is None:
            return len(raw_data)

        # NOTE: use processes for parallel data calculations and make true asynchronous work
        suitable_models = await self._loop.run_in_executor(self._process_pool,
                                                           query_converter_build,
                                                           self._model,
                                                           filter_obj,
                                                           raw_data)

        return len(list(suitable_models))

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
