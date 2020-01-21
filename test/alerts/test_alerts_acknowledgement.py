from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest

alerts_command = CommandFactory.get_command(
    [const.ALERTS_COMMAND, 'acknowledge', '1', 'comment_1'])
t = unittest.TestCase()

def init(args):
    pass

def test_patch_action(args):
    expected_output = 'acknowledge'
    actual_output = alerts_command.action()
    t.assertEqual(actual_output, expected_output)

def test_patch_options(args):
    expected_output = {'alert_id': '1', 'comment': 'comment_1'}
    actual_output = alerts_command.options()
    t.assertDictEqual(actual_output, expected_output)

def test_patch_method(args):
    expected_output = 'patch'
    actual_output = alerts_command.method('acknowledge')
    t.assertEqual(actual_output, expected_output)

test_list = [test_patch_action, test_patch_options, test_patch_method]
