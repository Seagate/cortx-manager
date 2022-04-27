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

from marshmallow import (Schema, fields, ValidationError)
from csm.core.controllers import  validators
import json
import unittest
from csm.test.common import Const

t = unittest.TestCase()
file_path = Const.MOCK_PATH

with open(file_path + "validator_data.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())

def init(args):
    pass

class TestSchema(Schema):
    username = fields.Str(validate=[validators.UserNameValidator()])
    password = fields.Str(validate=[validators.PasswordValidator()])
    path_prefix = fields.Str(validate=[validators.PathPrefixValidator()])
    comments = fields.Str(validate=[validators.CommentsValidator()])
    port = fields.Int(validate=[validators.PortValidator()])
    bucket_name = fields.Str(validate=[validators.BucketNameValidator()])

test_schema_obj = TestSchema()

def test_1(args):
    "user name test 1"
    expected_output = EXPECTED_OUTPUT.get("test_1", {})
    actual_output = test_schema_obj.load(expected_output)
    t.assertDictEqual(actual_output, expected_output)

def test_2(args):
    "TEST 2"
    data_list = EXPECTED_OUTPUT.get("test_2", [])
    for data in data_list:
        try:
            with t.assertRaises(ValidationError):
                test_schema_obj.load(data)
        except Exception as e:
            print(f"{e}")

test_list = [test_1, test_2]

    
