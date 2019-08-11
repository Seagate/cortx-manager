#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_file_collector.py
 Description:       Contains unit tests for various file collector classes.

 Creation Date:     03/07/2018
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

import unittest
import yaml
import os
import sys
import mock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from csm.common.log import Log
from csm.common.file_collector import RemoteFileCollector

class RemoteFileCollector(unittest.TestCase):
    """ Unit tests for RemoteFileCollector class """

    def setUp(self):
        Log.init("csm")
        collection_rules_yaml = '''
            s3_server:
                commands:
                    - ls -l /tmp
                    - uptime

                files:
                    - /etc/hosts

            mero:
                commands:
                    - ls -l /tmp
                    - uptime

                files:
                    - /etc/hosts
        '''
        self.target_path = "/tmp/bundle"
        self.components = ["s3_server"]
        self.summary_file_path = [self.target_path,  self.components[0], "summary.txt"]
        self.collection_rules = yaml.load(collection_rules_yaml)
        self.remote_file_collector = RemoteFileCollector(self.collection_rules, self.target_path)
        #'localhost', None, self.target_path)

        # Patch os
        self.patch_os = mock.patch("csm.utils.file_collector.os")
        self.mock_os = self.patch_os.start()
        self.mock_os_path = mock.MagicMock()
        self.mock_os_path_exists = mock.MagicMock()
        self.mock_os_path_join = mock.MagicMock()
        self.mock_os.path = self.mock_os_path
        self.mock_os.exists = self.mock_os_path_exists
        self.mock_os.path.join = self.mock_os_path_join

        # Patch shutils
        self.patch_shutil = mock.patch("csm.utils.file_collector.shutil")
        self.mock_shutil = self.patch_shutil.start()

        # Patch open built in
        self.patch_open = mock.patch("csm.utils.file_collector.open")
        self.mock_open = self.patch_open.start()
        self.mock_file = mock.MagicMock()
        self.mock_file.__enter__.return_value = mock.MagicMock()
        self.mock_open.return_value = self.mock_file

        # Patch subprocess
        self.patch_subprocess = mock.patch("csm.utils.file_collector.subprocess")
        self.mock_subprocess = self.patch_subprocess.start()

    def test_collect_target_path_exists(self):
        """
        Unit test for collect method.
        Scenario: Target path already exists.
        """

        # Preparation
        self.mock_os.path.exists.return_value = True
        self.mock_os.path.join.return_value = "/".join(self.summary_file_path[:2])
        self.mock_subprocess.check_output.return_value = "Test command output"

        # Actual call
        self.remote_file_collector.collect(self.components)

        # Assertions
        self.mock_shutil.rmtree.assert_called_with(self.mock_os.path.join.return_value)
        self.mock_os.mkdir.assert_called_with("/".join(self.summary_file_path[:2]))
        self.mock_os.path.join.assert_any_call(*self.summary_file_path)
        self.mock_open.assert_any_call(self.mock_os.path.join.return_value, "w")
        self.mock_open().__enter__().write.assert_any_call(
            self.mock_subprocess.check_output.return_value)


    def test_collect_target_path_not_exists(self):
        """
        Unit test for collect method.
        Scenario: Target path doesn't exist.
        """

        # Preparation
        self.mock_os.path.exists.return_value = False
        self.mock_os.path.join.return_value = "/".join(self.summary_file_path[:2])
        self.mock_subprocess.check_output.return_value = "Test command output"

        # Actual call
        self.remote_file_collector.collect(self.components)

        # Assertions
        self.assertEqual(self.mock_shutil.rmtree.called, False)
        self.mock_os.mkdir.assert_called_with("/".join(self.summary_file_path[:2]))
        self.mock_os.path.join.assert_any_call(*self.summary_file_path)
        self.mock_open.assert_any_call(self.mock_os.path.join.return_value, "w")
        self.mock_open().__enter__().write.assert_any_call(
            self.mock_subprocess.check_output.return_value)

    def test_collect_target_path_permission_issue(self):
        """
        Unit test for collect method.
        Scenario: Permission denied for target directory creation.
        """

        # Preparation
        self.mock_os.path.exists.return_value = False
        self.mock_os.path.join.return_value = "/".join(self.summary_file_path[:2])
        self.mock_subprocess.check_output.return_value = "Test command output"
        self.mock_os.mkdir.side_effect = OSError('Permission denied')

        # Actual call
        with self.assertRaises(OSError):
            self.remote_file_collector.collect(self.components)

        # Assertions
        self.assertEqual(self.mock_shutil.rmtree.called, False)

    def test_collect_invalid_component(self):
        """
        Unit test for collect method.
        Scenario: Invalid component.
        """

        # Preparation
        self.mock_os.path.exists.return_value = False
        self.mock_os.path.join.return_value = "/".join(self.summary_file_path[:2])
        self.mock_subprocess.check_output.return_value = "Test command output"

        # Actual call
        with self.assertRaises(Exception):
            self.remote_file_collector.collect(["some"])


unittest.main()
