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

import unittest

from csm.cli.command_factory import CommandFactory
from csm.core.blogic import const

alerts_command = CommandFactory.get_command([const.ALERTS_COMMAND, 'show', '-f', 'json'],
                                            {const.ALERTS_COMMAND: {'list': True}})

t = unittest.TestCase()


def test_get_name():
    expected_output = "csm.cli.command"
    actual_output = alerts_command.__module__
    t.assertEqual(actual_output, expected_output)


def test_get_action():
    expected_output = 'show'
    actual_output = alerts_command.sub_command_name
    t.assertEqual(actual_output, expected_output)


def test_get_options():
    expected_output = {
        'comm': {
            'json': {},
            'method': 'get',
            'params': {'duration': '', 'limit': '', 'show_active': '', 'show_all': ''},
            'target': '/{version}/alerts', 'type': 'rest', 'version': 'v1'},
        'duration': '60s',
        'format': 'json',
        'limit': 1000,
        'need_confirmation': False,
        'output': {
            'table': {
                'filters': 'alerts',
                'headers': {
                    'acknowledged': 'Acknowledged',
                    'alert_uuid': 'Alert Id',
                    'description': 'Description',
                    'health': 'Health',
                    'resolved': 'Resolved',
                    'severity': 'Severity',
                    'state': 'State'}}},
        'show_active': 'false',
        'show_all': 'false',
        'sub_command_name': 'show'}
    actual_output = alerts_command.options
    t.assertDictEqual(actual_output, expected_output)


def test_get_method():
    expected_output = 'get'
    actual_output = alerts_command.method
    t.assertEqual(actual_output, expected_output)


def test_invalid_arg():
    with t.assertRaises(SystemExit) as cm:
        CommandFactory.get_command([const.ALERTS_COMMAND, 'show', '-b', 'json'],
                                   {const.ALERTS_COMMAND: {'list': True}})
    t.assertEqual(cm.exception.code, 2)


def test_incorrect_format():
    with t.assertRaises(SystemExit) as cm:
        CommandFactory.get_command([const.ALERTS_COMMAND, 'show', '-f', 'abc'],
                                   {const.ALERTS_COMMAND: {'list': True}})
    t.assertEqual(cm.exception.code, 2)


test_list = [test_get_name, test_get_action, test_get_options, test_get_method, test_invalid_arg,
             test_incorrect_format]
