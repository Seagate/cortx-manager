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
import mock
from argparse import Namespace

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from cortx.utils.log import Log
from csm.api.api_client import CsmApiClient

class CsmApiClientTest(unittest.TestCase):
    """ Unit tests for command factory class.  """
    def setUp(self):
        Log.init("csm", log_path=".")
        self.csm_api_client = CsmApiClient()
        self.command = mock.MagicMock()
        self.command.name.return_value = 'support_bundle'
        self.command.action.return_value = 'create'
        self.command.args.return_value = Namespace(args=[])

    def test_call(self):
        """ Test functionality of call method.  """

        response = self.csm_api_client.call(self.command)
        print('rc=%d output=%s' %(response.rc(), response.output()))

        self.assertEqual(response.rc(), 0)

    def test_support_bundle(self):
        """ Test functionality of support_bundle method.  """
        expected_value = "support_bundle: {'action': 'create'}"

        actual_value = self.csm_api_client.call(self.command)

        self.assertEqual(actual_value, expected_value)
