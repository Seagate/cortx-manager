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

alerts_comment_show = CommandFactory.get_command([const.ALERTS_COMMAND, 'comment', 'show', ""],
                                                 {const.ALERTS_COMMAND: {'list': True}})

t = unittest.TestCase()


def test_show_action():
    expected_output = 'show'
    actual_output = alerts_comment_show.sub_command_name
    t.assertEqual(actual_output, expected_output)


def test_show_options():
    expected_output = {
        'alert_uuid': '',
        'comm': {
            'json': {},
            'method': 'get',
            'params': {},
            'target': '/{version}/alerts/{alert_uuid}/comments',
            'type': 'rest',
            'version': 'v1'},
        'format': 'table',
        'need_confirmation': False,
        'output': {
            'table': {
                'filters': 'comments',
                'headers': {
                    'comment_id': 'Comment Id',
                    'comment_text': 'Comment',
                    'created_by': 'Created By',
                    'created_time': 'Created Time'}}},
        'sub_command_name': 'show'}
    actual_output = alerts_comment_show.options
    t.assertDictEqual(actual_output, expected_output)


def test_show_method():
    expected_output = 'get'
    actual_output = alerts_comment_show.method
    t.assertEqual(actual_output, expected_output)


def test_add_action():
    expected_output = 'show'
    actual_output = alerts_comment_show.sub_command_name
    t.assertEqual(actual_output, expected_output)


def test_add_options():
    expected_output = {
        'alert_uuid': '',
        'comm': {
            'json': {},
            'method': 'get',
            'params': {},
            'target': '/{version}/alerts/{alert_uuid}/comments',
            'type': 'rest',
            'version': 'v1'},
        'format': 'table',
        'need_confirmation': False,
        'output': {
            'table': {
                'filters': 'comments',
                'headers': {
                    'comment_id': 'Comment Id',
                    'comment_text': 'Comment',
                    'created_by': 'Created By',
                    'created_time': 'Created Time'}}},
        'sub_command_name': 'show'}
    actual_output = alerts_comment_show.options
    t.assertDictEqual(actual_output, expected_output)


def test_add_method():
    expected_output = 'get'
    actual_output = alerts_comment_show.method
    t.assertEqual(actual_output, expected_output)


test_list = [test_show_action, test_show_options, test_show_method,
             test_add_action, test_add_options, test_add_method]
