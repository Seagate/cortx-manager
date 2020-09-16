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

alerts_command = CommandFactory.get_command([const.ALERTS_COMMAND, 'acknowledge', '1', 'comment_1'],
                                            {const.ALERTS_COMMAND: {'update': True}})
t = unittest.TestCase()


def test_patch_action():
    expected_output = 'acknowledge'
    actual_output = alerts_command.sub_command_name
    t.assertEqual(actual_output, expected_output)


def test_patch_options():
    expected_output = {
        'acknowledged': False,
        'alerts_id': '1',
        'comm': {
            'json': {'acknowledged': ''},
            'method': 'patch',
            'params': {},
            'target': '/{version}/alerts/{alerts_id}',
            'type': 'rest',
            'version': 'v1'},
        'need_confirmation': True,
        'output': {'success': 'Alert Updated.'},
        'sub_command_name': 'acknowledge'}
    actual_output = alerts_command.options
    t.assertDictEqual(actual_output, expected_output)


def test_patch_method():
    expected_output = 'patch'
    actual_output = alerts_command.method
    t.assertEqual(actual_output, expected_output)


test_list = [test_patch_action, test_patch_options, test_patch_method]
