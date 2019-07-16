#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          test_api_client.py
 Description:       Unit test for api clients.

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
import os
import unittest
import mock
from argparse import Namespace

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from csm.common.log import Log
from csm.api.api_client import CsmApiClient

class CsmApiClientTest(unittest.TestCase):
    """ Unit tests for command factory class.  """
    def setUp(self):
        Log.init("csm")
        self.csm_api_client = CsmApiClient()
        self.command = mock.MagicMock()
        self.command.name.return_value = 'support_bundle'
        self.command.action.return_value = 'create'
        self.command.args.return_value = Namespace(args=[])

    def test_call(self):
        """ Test functionality of call method.  """

        response = self.csm_api_client.call(self.command)
        print 'rc=%d output=%s' %(response.rc(), response.output())

        self.assertEqual(response.rc(), 0)

    def test_support_bundle(self):
        """ Test functionality of support_bundle method.  """
        expected_value = "support_bundle: {'action': 'create'}"

        actual_value = self.csm_api_client.call(self.command)

        self.assertEqual(actual_value, expected_value)
