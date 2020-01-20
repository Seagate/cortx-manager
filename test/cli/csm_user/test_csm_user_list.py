#!/usr/bin/env python3

from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os
from csm.test.common import Const

show_command = CommandFactory.get_command(
    ["user", 'show'])
t = unittest.TestCase()
file_path = Const.MOCK_PATH

with open(file_path + "csm_user_commands_output.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())


def test_1(*args):
    expected_output = 'user'
    actual_output = show_command.name
    t.assertEqual(actual_output, expected_output)


def test_2(*args):
    expected_output = EXPECTED_OUTPUT.get("expected_csm_user_show")
    actual_output = show_command.options
    t.assertDictEqual(actual_output, expected_output)


def test_3(*args):
    expected_output = 'get'
    actual_output = show_command.method
    t.assertEqual(actual_output, expected_output)


def init(args):
    pass


test_list = [test_1, test_2, test_3]
