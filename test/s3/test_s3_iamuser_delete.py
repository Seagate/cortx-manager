#!/usr/bin/env python3

from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os
from csm.test.common import Const

permissions = {
"s3iamusers": {"list": True, "delete": True, "create": True }
}

accounts_command = CommandFactory.get_command(
    ["s3iamuser", 'delete', 'csm_user'], permissions)
t = unittest.TestCase()
file_path = Const.MOCK_PATH

with open(file_path + "s3_commands_output.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())

def test_1(*args):
    expected_output = 's3iamuser'
    actual_output = accounts_command.name
    t.assertEqual(actual_output, expected_output)

def test_2(*args):
    
    expected_output = EXPECTED_OUTPUT.get("iamuser", {}).get("delete_test_2", {})
    actual_output = accounts_command.options
    t.assertDictEqual(actual_output, expected_output)

def test_3(*args):
    expected_output = 'delete'
    actual_output = accounts_command.method
    t.assertEqual(actual_output, expected_output)
        
def init(args):
    pass    
    
test_list = [test_1, test_2, test_3]
