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

#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          Validate.py
 Description:       Compare JsonSchema marshmallow and Schematics validation
                    from efficiency.

 Creation Date:     10/19/2019
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

# Removed python package jsonschema from csm.
# Following test is not valid.
# TODO:Code clean up task will ne covered in future sprint.
import jsonschema
import json
import timeit
from marshmallow import Schema, fields, pprint, ValidationError
from schematics.models import Model
from schematics.types import StringType, DecimalType, DateTimeType, IntType
from schematics.types.compound import DictType, ModelType, ListType
from schematics.exceptions import ValidationError


NUMBER_OF_TIMES = 10000000
"""
Marshmallow schema creation
"""


class ValidateInfo(Schema):
    status = fields.Str(required=True)
    dc12v = fields.Int(required=True)
    dc_temp = fields.Int(required=True)
    vendor = fields.Str(required=True)
    description = fields.Str(required=True)


class ValidateExtendedInfo(Schema):
    position = fields.Str(required=True)
    durable_id = fields.Str(required=True)


class ValidateEnclosurePsuAlert(Schema):
    info = fields.Nested(ValidateInfo, required=True)
    alert_type = fields.Str(required=True)
    extended_info = fields.Nested(ValidateExtendedInfo, required=True)
    resource_type = fields.Str(required=True)


class ValidateSspl2MsgHeader(Schema):
    msg_version = fields.Str(required=True)
    schema_version = fields.Str(required=True)
    sspl_version = fields.Str(required=True)


class SensorResponseTypeMarshmallow(Schema):
    enclosure_psu_alert = fields.Nested(ValidateEnclosurePsuAlert, required=True)


class ValidateMessage(Schema):
    sspl_ll_msg_header = fields.Nested(ValidateSspl2MsgHeader, required=True)
    sensor_response_type = fields.Nested(SensorResponseTypeMarshmallow, required=True)


class ValidateJson(Schema):
    username = fields.Str(required=True)
    description = fields.Str(required=True)
    title = fields.Str(required=True)
    expires = fields.Int(required=True)
    signature = fields.Str(required=True)
    # time = fields.Function(lambda obj: datetime.datetime.strptime(
    #                             obj.get('time'), '%Y-%m-%d %H:%M:%S.%f'))
    message = fields.Nested(ValidateMessage, required=True)
    time = fields.DateTime(required=True, format='%Y-%m-%d %H:%M:%S.%f')


"""
schematics schema creation 
"""


class SsplMsgHeader(Model):
    msg_version = StringType(required=True)
    schema_version = StringType(required=True)
    sspl_version = StringType(required=True)


class AlertInfo(Model):
    status = StringType(required=True)
    dc12v = IntType(required=True)
    dc_temp = IntType(required=True)
    vendor = StringType(required=True)
    description = StringType(required=True)


class ExtendedInfo(Model):
    position = StringType(required=True)
    durable_id = StringType(required=True)


class EnclosurePsuType(Model):
    info = ModelType(AlertInfo)
    alert_type = StringType(required=True)
    extended_info = ModelType(ExtendedInfo)
    resource_type = StringType(required=True)


class SensorResponseType(Model):
    enclosure_psu_alert = ModelType(EnclosurePsuType)


class Message(Model):
    sspl_ll_msg_header = ModelType(SsplMsgHeader)
    sensor_response_type = ModelType(SensorResponseType)


class BaseAlerts(Model):
    username = StringType(required=True)
    description = StringType(required=True)
    title = StringType(required=True)
    expires = IntType(required=True)
    signature = StringType(required=True)
    time = StringType(required=True)
    message = ModelType(Message)


def json_validator():
    jsonschema.validate(json_obj, schema)
    pprint(json_obj)


def marshmallow_validator():
    validate = ValidateJson()
    try:
        data = validate.load(json_obj)
        pprint(data)
    except ValidationError as ve:
        pprint(ve.messages)
        # print(ve.valid_data)


def json_validator_time():
    setup_code = 'from __main__ import json_validator'
    test_code = 'json_validator'
    times = timeit.repeat(setup=setup_code,
                          stmt=test_code,
                          repeat=3,
                          number=NUMBER_OF_TIMES)

    print('json_validator time: {}'.format(sum(times)))


def marshmallow_validator_time():
    setup_code = 'from __main__ import marshmallow_validator'
    test_code = 'marshmallow_validator'
    times = timeit.repeat(setup=setup_code,
                          stmt=test_code,
                          repeat=3,
                          number=NUMBER_OF_TIMES)

    print('marshmallow_validator time: {}'.format(sum(times)))


def schematics_validator():
    try:
        alerts = BaseAlerts(json_obj)
        alerts.validate()
    except ValidationError as ve:
        pprint(ve.messages)


def schematics_validator_time():
    setup_code = 'from __main__ import schematics_validator'
    test_code = 'schematics_validator'

    times = timeit.repeat(setup=setup_code,
                          stmt=test_code,
                          repeat=3,
                          number=NUMBER_OF_TIMES)

    print('schematics_validator time: {}'.format(sum(times)))


if __name__ == "__main__":
    with open('schema/sspl_schema.json', 'r') as f:
        schema_data = f.read()
        schema = json.loads(schema_data)

    with open('schema/test_sspl.json', 'r') as f:
        json_data = f.read()
        json_obj = json.loads(json_data)

    for i in range(1):
        schematics_validator_time()
        marshmallow_validator_time()
        json_validator_time()
