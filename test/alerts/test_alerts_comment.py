#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_alerts_comment.py
 Description:       Alerts Comment Add and Show

 Creation Date:     17/03/2020
 Author:            Prathamesh Rodi


 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest

alerts_comment_show = CommandFactory.get_command(
    [const.ALERTS_COMMAND, 'comment', 'show', ""])
alerts_comment_show = CommandFactory.get_command(
    [const.ALERTS_COMMAND, 'comment', 'show', ""])
t = unittest.TestCase()

def init(args):
    pass

def test_show_action(args):
    expected_output = 'show'
    actual_output = alerts_comment_show.action()
    t.assertEqual(actual_output, expected_output)

def test_show_options(args):
    expected_output = {'alert_id': '1', 'comment': 'comment_1'}
    actual_output = alerts_comment_show.options()
    t.assertDictEqual(actual_output, expected_output)

def test_show_method(args):
    expected_output = 'get'
    actual_output = alerts_comment_show.method('comment')
    t.assertEqual(actual_output, expected_output)

def test_add_action(args):
    expected_output = 'show'
    actual_output = alerts_comment_show.action()
    t.assertEqual(actual_output, expected_output)

def test_add_options(args):
    expected_output = {'alert_id': '1', 'comment': 'comment_1'}
    actual_output = alerts_comment_show.options()
    t.assertDictEqual(actual_output, expected_output)

def test_add_method(args):
    expected_output = 'get'
    actual_output = alerts_comment_show.method('comment')
    t.assertEqual(actual_output, expected_output)

test_list = [test_show_action, test_show_options, test_show_method,
             test_add_action, test_add_options, test_add_method]
