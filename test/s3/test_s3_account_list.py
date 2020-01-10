from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os 


accounts_command = CommandFactory.get_command(
    ["s3accounts", 'show' ])
t = unittest.TestCase()

with open(os.path.dirname(os.path.realpath(__file__))+"/s3_commands_output.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())

def test_1(*args):
    expected_output = 's3accounts'
    actual_output = accounts_command.name
    t.assertEqual(actual_output, expected_output)

def test_2(*args):
    
    expected_output = EXPECTED_OUTPUT.get("accounts").get("show_test_2", {})
    actual_output = accounts_command.options
    t.assertDictEqual(actual_output, expected_output)

def test_3(*args):
    expected_output = 'get'
    actual_output = accounts_command.method
    t.assertEqual(actual_output, expected_output)
        
def init(args):
    pass    
    
test_list = [test_1, test_2, test_3]
