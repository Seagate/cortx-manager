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
from cortx.utils.cli_framework.command_factory import CommandFactory
from cortx.utils.cli_framework.command import Output
from csm.core.providers.providers import Response
from argparse import ArgumentError
import unittest
import json
import os
import sys
from csm.test.common import Const

permissions = {
            'appliance_info': { 'read': True }
}

show_csm_command = CommandFactory.get_command(
    ["appliance_info", "show"], permissions, Const.CLI_SCHEMA_PATH, [], [])

t = unittest.TestCase()
file_path = Const.MOCK_PATH

obtained_output_file = os.path.join("/tmp","appliance_info_table_obtained_output")
with open(file_path + "about/appliance_info_cmd_expceted_output_table") as fp:
    EXPECTED_OUTPUT = fp.readlines()

with open(file_path + "about/appliance_info_api_response") as fp:
    API_RESPONSE =  json.loads(fp.read())


with open(file_path + "about/appliance_info_commands_output.json") as fp:
    COMMANDS_OUTPUT = json.loads(fp.read())


def test_command_name(*args):
    expected_output = 'appliance_info'
    actual_output = show_csm_command.name
    t.assertEqual(actual_output, expected_output)


def test_command_options(*args):
    expected_output = COMMANDS_OUTPUT.get("expected_appliance_info_show")
    actual_output = show_csm_command.options
    t.assertDictEqual(actual_output, expected_output)


def test_command_method(*args):
    expected_output = 'get'
    actual_output = show_csm_command.method
    t.assertEqual(actual_output, expected_output)

def test_commandoutput_data(*args):
    response = Response(output=API_RESPONSE)
    op = Output(show_csm_command, response)
    with open(obtained_output_file,"w") as obtained_output:
        op.dump(out=obtained_output, err=sys.stderr,response=response,
                output_type=show_csm_command.options.get("format"),
                **show_csm_command.options.get("output"))
    with open(obtained_output_file) as obtained_output:
        t.assertEqual(EXPECTED_OUTPUT, obtained_output.readlines())


def init(args):
    pass


test_list = [test_command_name, test_command_options, test_command_method, test_commandoutput_data]
