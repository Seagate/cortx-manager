# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

from cortx.utils.data.access.filters import Compare, And, Or
from schematics.exceptions import ConversionError
from csm.common.errors import InvalidRequest
import urllib.parse
import re

class Filter:
    """Query to filter_object builder"""

    def _parse_query(query):
        """
        Segregate list of key_val pairs and operands.
        :param query: string of key_val pairs and operands like: "key1=value1 AND key2=value2 OR key3=value3"
        :returns: dict(key_value_fields), dictionary of key and value pairs
        :returns: operations, Ordered list of operations to be performed on give field and value pairs
        """
        operations = []
        key_value_fields = []
        if query:
            fields = list(re.split(' OR | AND ', query))
            key_value_fields = [(map(str.strip, key.split('=', 1))) for key in fields]
            fields = list(query.split(" "))
            operations = [key for key in fields if key in ("AND", "OR")]
        return dict(key_value_fields), operations

    def _validate_query_fields(fields, model):
        """
        Validate and provide default values for those keys whose values are invalid for given field.
        :param fields: collection of key value pairs received as input
        :param Type[BaseModel] model: model for constructing data mapping for index
        :returns: Updated key_value pairs
        """
        default_val_dict = model().to_native()
        updated_key_val = {}
        for key, value in fields.items():
            try:
                field = eval(f"model.{key}")
                _ = field.to_native(value)
            except AttributeError:
                raise InvalidRequest(f"key {key} not found")
            except ConversionError:
                updated_key_val[key] = default_val_dict[key]
        return updated_key_val

    @staticmethod
    def prepare_filters(query, model):
        """
        Prepare filter object from plain query like "{field1=val1 OR field2=val2 AND field3=val3}"
        :param query: nested query, here query could be encoded "{field1%3Dval1 OR field2%3Dval2 AND field3%3Dval3}"
        :param Type[BaseModel] model: model for constructing data mapping for index
        :returns: IFilter filter_obj
        """
        query = [urllib.parse.unquote(query)]
        query, operations = Filter._parse_query(query[0][1:-1])
        updated_fields = Filter._validate_query_fields(query, model)
        query.update(updated_fields)
        db_conditions = []
        nested_operations = 0
        filter_obj = []
        for key, value in query.items():
            db_conditions.append(Compare(eval(f"model.{key}"), "=", value))
            if len(db_conditions) > 1:
                filter_obj.clear()
                if operations[nested_operations] == "AND":
                    filter_obj.append(And(*db_conditions))
                else:
                    filter_obj.append(Or(*db_conditions))
                nested_operations += 1
                db_conditions.clear()
                db_conditions = [*filter_obj]
        if not db_conditions:
            raise InvalidRequest("Empty query found")
        return db_conditions[0]
        