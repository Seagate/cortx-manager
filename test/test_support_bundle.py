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

import asyncio
import json
import unittest

from csm.cli.command_factory import CommandFactory
from csm.cli.support_bundle.support_bundle import SupportBundle
from csm.test.common import Const

t = unittest.TestCase()
PERMISSIONS = {
    "support_bundle": {"create": True, "list": True},
    "bundle_generate": {"create": True},
    "csm_bundle_generate": {"create": True}}
with open(f"{Const.MOCK_PATH}support_bundle.json") as fp:
    RESPONSE_DATA = json.loads(fp.read())


def test_1():
    command = CommandFactory.get_command(["support_bundle", "generate", "Test Comment"],
                                         PERMISSIONS)
    actual_output = command.options
    expected_output = RESPONSE_DATA.get("generate", {}).get("test_1", {})
    t.assertDictEqual(actual_output, expected_output)


def test_2():
    command = CommandFactory.get_command(["support_bundle", "generate", "Test Comment"],
                                         PERMISSIONS)
    loop = asyncio.get_event_loop()
    resp = loop.run_until_complete(SupportBundle.bundle_generate(command))
    loop.close()
    t.assertEqual(resp.rc(), 0x0000)


def test_3():
    command = CommandFactory.get_command(["support_bundle", "generate", "BUNDLE_ID"], PERMISSIONS)
    loop = asyncio.get_event_loop()
    resp = loop.run_until_complete(SupportBundle.bundle_status(command))
    loop.close()
    t.assertEqual(resp.rc(), 0x0000)


test_list = [test_1, test_2, test_3]
