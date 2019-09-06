from csm.core.blogic import const
from csm.cli.command_factory import CommandFactory
from argparse import ArgumentError
import unittest

alerts_command = CommandFactory.get_command(
    [const.ALERTS_COMMAND, 'show', '-f', 'json'])
t = unittest.TestCase()

def test_get_name():
    expected_output = "csm.cli.commands"
    actual_output = alerts_command.__module__
    t.assertEqual(actual_output, expected_output)

def test_get_action():
    expected_output = 'show'
    actual_output = alerts_command.action()
    t.assertEqual(actual_output, expected_output)

def test_get_options():
    expected_output = {'all': 'false', 'duration': '60s', 'format': 'json',
                       'no_of_alerts': 1000}
    actual_output = alerts_command.options()
    t.assertDictEqual(actual_output, expected_output)

def test_get_method():
    expected_output = 'get'
    actual_output = alerts_command.method('show')
    t.assertEqual(actual_output, expected_output)

def test_invalid_arg():
    with t.assertRaises(ArgumentError) as context:
        CommandFactory.get_command(
            [const.ALERTS_COMMAND, 'show', '-b', 'json'])

def test_incorrect_format():
    with t.assertRaises(ArgumentError) as context:
        CommandFactory.get_command(
            [const.ALERTS_COMMAND, 'show', '-f', 'abc'])

test_list = [test_get_name, test_get_action, test_get_options, test_get_method]

if __name__ == '__main__':
    test_incorrect_format()