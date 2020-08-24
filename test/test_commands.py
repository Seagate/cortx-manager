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

import sys
import os
import unittest
from mock import MagicMock, call

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory


class SupportBundleTest(unittest.TestCase):
    """
        Unit tests for support bundle class.
    """

    def setUp(self):
        self.support_bundle = CommandFactory.get_command(
            [const.SUPPORT_BUNDLE, "create"])

    def test_get_name(self):
        """
            Test get_name method.
        """

        expected_output = "csm.cli.commands"
        actual_output = self.support_bundle.__module__

        self.assertEqual(actual_output, expected_output)

    def test_get_args(self):
        """
            Test get_args method.
        """

        expected_output = 'create'

        actual_output = self.support_bundle._args.action

        self.assertEqual(actual_output, expected_output)

    def test_add_args(self):
        """
            Test add_args method.
        """

        mock_subparser = MagicMock()
        self.support_bundle.add_args(mock_subparser)
        expected_call = call(
            'support_bundle', help='Create, list or delete support bundle.')

        actual_call = mock_subparser.add_parser.call_args

        self.assertEqual(actual_call, expected_call)
