#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_support_bundle.py
 Description:       Test support bundle functionality for generating and status.


 Creation Date:     3/6/2020
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os
import json, unittest
from csm.cli.command_factory import CommandFactory
from csm.cli.support_bundle.support_bundle import SupportBundle
from csm.test.common import Const

t = unittest.TestCase()
PERMISSIONS = {
    "support_bundle": {
        "create": True,
        "list": True
    },
    "bundle_generate": {
        "create": True
    },
    "csm_bundle_generate": {
        "create": True
    }
}
with open(f"{Const.MOCK_PATH}support_bundle.json") as fp:
    RESPONSE_DATA = json.loads(fp.read())
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def init(args):
    pass

with open(Const.MOCK_PATH + "support_bundle.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())

def test_1():
    command = CommandFactory.get_command(["support_bundle", "generate",
                                          "Test Comment"], PERMISSIONS)
    actual_output = command.options
    expected_output = RESPONSE_DATA.get("generate", {}).get("test_1", {})
    t.assertDictEqual(actual_output, expected_output)

def test_2():
    command = CommandFactory.get_command(["support_bundle", "generate",
                                        "Test Comment"], PERMISSIONS)
    resp = SupportBundle.bundle_generate(command)
    t.assertEqual(resp.rc(), 0x0000)

def test_3():
    command = CommandFactory.get_command(["support_bundle", "generate",
                                        "BUNDLE_ID"], PERMISSIONS)
    resp = SupportBundle.bundle_status(command)
    t.assertEqual(resp.rc(), 0x0000)

test_list = [test_1, test_2, test_3]
