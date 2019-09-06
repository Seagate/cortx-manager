"""
 ****************************************************************************
 Filename:          schema.py
 Description:       Contains functionality for alert plugin.

 Creation Date:     03/09/2019
 Author:            Pawan Kumar Srivastava

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
from csm.common.payload import *
from csm.core.blogic import const
from csm.common.log import Log

class Schema:
    """
    This class is responsible to serialize and deserialize a dictonary.
    This will also convert one schema to another based on a mapping file.
    """

    def __init__(self):
        self._mapping_table = {}
        self._load_mapping_table()

    def _load_mapping_table(self):
        """
        This method loads the mapping table into the memory.
        """
        try:
            mapping_file = Json(const.ALERT_MAPPING_TABLE)
            self._mapping_table = mapping_file.load()
        except Exception as e:
            Log.exception(e)

    def serialize(self, message):
        """
        This method will serialize the dictionary.
        i.e. Input - { "x": { "y": { "z": 20}}, "a": { "b": { "c": 10}}}
        Output - {'x.y.z': 20, 'a.b.c': 10}
        """
        data = {}
        try:
            if type(message) is not dict:
                return None
            for key in message.keys():
                sub_data = self.serialize(message[key])
                if sub_data is None:
                    data[key] = message[key]
                    continue
                for sub_key in sub_data.keys():
                    new_key = '%s.%s' %(key, sub_key)
                    data[new_key] = sub_data[sub_key]
        except Exception as e:
            Log.exception(e)
        return data

    def deserialize(self, message:dict, out_message={}):
        """
        This method will deserialize the dictionary.
        i.e Input - {'x.y.z': 20, 'a.b.c': 10}
        Output - { "x": { "y": { "z": 20}}, "a": { "b": { "c": 10}}}
        """
        try:
            for key in message.keys():
                if '.' not in key:
                    out_message[key] = message[key]
                else:
                    new_key = key.split('.')
                    rem_key = new_key.pop(0)
                    if rem_key not in out_message:
                        out_message[rem_key] = {}
                    self.deserialize({".".join(new_key): message[key]},\
                        out_message[rem_key])
        except Exception as e:
            Log.exception(e)
        return out_message

    def map_schema(self, type, serialize_data):
        """
        This method will use the mapping table to convert the serialized
        input schema to serialized output schema.
        """
        output_schema = {}
        try:
            data = self._mapping_table.get(type, {})
            for key in serialize_data:
                if key in data:
                    output_schema[data[key]] = serialize_data[key]
        except Exception as e:
            Log.exception(e)
        return output_schema
