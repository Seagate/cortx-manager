#!/usr/bin/env python3

from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os
from csm.test.common import Const

file_path = Const.MOCK_PATH
create_command = CommandFactory.get_command(
    ["user", 'create', "User1234", "-p", "Qwerty@123"])
t = unittest.TestCase()

with open(file_path + "csm_user_commands_output.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())


def test_1(*args):
    expected_output = 'user'
    actual_output = create_command.name
    t.assertEqual(actual_output, expected_output)


def test_2(*args):
    expected_output = EXPECTED_OUTPUT.get("expected_csm_user_create")
    actual_output = create_command.options
    t.assertDictEqual(actual_output, expected_output)


def test_3(*args):
    expected_output = 'post'
    actual_output = create_command.method
    t.assertEqual(actual_output, expected_output)


def init(args):
    pass


test_list = [test_1, test_2, test_3]
