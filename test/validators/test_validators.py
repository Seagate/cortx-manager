#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_validators.py
 Description:       Test Marshmallow Validators Class.

 Creation Date:     12/20/2019
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from marshmallow import (Schema, fields, ValidationError, validate,
                         validates_schema)
from csm.core.controllers import  validators
from eos.utils.log import Log
import os
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
    
    
    
