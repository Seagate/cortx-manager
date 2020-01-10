"""
 ****************************************************************************
 Filename:          test_s3_bucket_list.py
 Description:       Test S3 bucket list CLI.

 Creation Date:     12/13/2019
 Author:            Soniya Moholkar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os

accounts_command = CommandFactory.get_command(
    ["s3bucket", 'show'])
t = unittest.TestCase()

with open(os.path.dirname(os.path.realpath(__file__)) + "/s3_bucket_commands_output.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())


def test_1(*args):
    expected_output = 's3bucket'
    actual_output = accounts_command.name
    t.assertEqual(actual_output, expected_output)


def test_2(*args):
    expected_output = EXPECTED_OUTPUT.get("buckets").get("show_test_2", {})
    actual_output = accounts_command.options
    t.assertDictEqual(actual_output, expected_output)


def test_3(*args):
    expected_output = 'get'
    actual_output = accounts_command.method
    t.assertEqual(actual_output, expected_output)


def init(args):
    pass


test_list = [test_1, test_2, test_3]
