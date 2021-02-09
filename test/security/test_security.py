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
 
from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os
from csm.test.common import Const
 
permissions = {
            'security': { 'read': True }
}
 
show_command = CommandFactory.get_command(
    ["security","details"], permissions)
t = unittest.TestCase()
 
def test_1(*args):
    expected_output = 'security'
    actual_output = show_command.name
    t.assertEqual(actual_output, expected_output)
 
def test_2(*args):
    expected_output = 'get'
    actual_output = show_command.method
    t.assertEqual(actual_output, expected_output)
 
def init(args):
    pass
 
test_list = [test_1, test_2]