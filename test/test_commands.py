#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_commands.py
 Description:       Unit test for commands.

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
