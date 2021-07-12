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
from csm.core.blogic.models import CsmModel
import urllib.parse

class Filter():
    """Query to filter_object builder"""
    @staticmethod
    def parse_query(fields_of_filter):
        """
        Segregate list of key_val pairs and operands.
        :param fields_of_filter: list of key_val pairs and operands like ['field1=val1', 'operand1', 'field2=val2']
        :returns: dict(key_val_fields), dictionary of field(key) and value pairs
        :returns: operations, Ordered list of operations to be performed on give field and value pairs  
        """
        operations = []
        key_val_fields = []
        for key in fields_of_filter:
            if key:
                if key == "OR" or key == "AND":
                    operations.append(key)
                else:
                    key_val_fields.append(map(str.strip, key.split('=', 1)))
        return dict(key_val_fields), operations

    @staticmethod
    def _prepare_filters(query_rcvd, model):
        """
        Prepare filter object from plain query like "{field1=val1 OR field2=val2 AND field3=val3}"
        :param query_rcvd: nested query, here query_rcvd could be encoded "{field1%3Dval1 OR field2%3Dval2 AND field3%3Dval3}"
        :param Type[BaseModel] model: model for constructing data mapping for index
        :returns: IFilter filter_obj 
        """
        query = [urllib.parse.unquote(query_rcvd)]
        query_fields, operations = Filter.parse_query(list(query[0][1:-1].split(" ")))
        db_conditions = []
        nested_operations = 0
        filter_obj = []
        for key, value in query_fields.items():
            if not (db_conditions):
                try:
                    db_conditions.append(Compare(eval(f"model.{key}"), "=", value))
                except AttributeError as err:
                    raise Exception(f"Attribute {key} not found in a model: {err}")
                continue
            try:
                db_conditions.append(Compare(eval(f"model.{key}"), "=", value))
            except AttributeError as err:
                raise Exception(f"Attribute {key} not found in a model: {err}")
            filter_obj.clear()
            if operations[nested_operations] == "AND":
                filter_obj.append(And(*db_conditions))
            else:
                filter_obj.append(Or(*db_conditions))
            nested_operations += 1
            db_conditions.clear()
            db_conditions = [*filter_obj]
        if len(query_fields) == 1:
            return db_conditions[0]
        else:
            try:
                return filter_obj[0]
            except (IndexError):
                raise Exception("Empty query_parameters passed")
