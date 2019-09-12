#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          commands.py
 Description:       Represents RAS Command and arguments to help parsing
                    command line

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

import abc
import argparse
import errno

from csm.core.blogic import const
from csm.cli.csm_client import Output
from csm.common.errors import CsmError


class Command:
    """ Base class for all commands supported by RAS CLI """

    def __init__(self, action, options, args):
        self._action = action
        self._options = options
        self._args = args
        self._method = {}
        self.validate_command()
        self.update_options()

    @property
    def name(self):
        return self._name

    @property
    def action(self):
        return self._action

    @property
    def options(self):
        return self._options

    @property
    def args(self):
        return self._args

    def get_method(self, action):
        return self._method.get(action, 'get')

    def validate_command():
        pass

    def update_options():
        pass

    def process_response(self, response, out, err):
        """Process Response as per display method in format else normal display"""
        output_obj = Output(response)
        return output_obj.dump(out, err,
                               headers=self._headers, filters=self._filter,
                               output_format=self._options.get('format', None))


class SetupCommand(Command):
    """ Contains functionality to initialization CSM """

    _name = const.CSM_SETUP_CMD

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.CSM_SETUP_CMD, help='Setup csm.')
        sbparser.add_argument('action', help='action',
                              choices=const.CSM_SETUP_ACTIONS)
        sbparser.add_argument('-f', help='force',
                              action="store_true", default=False)
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=SetupCommand)


class SupportBundleCommand(Command):
    """ Contains functionality to handle support bundle """

    _name = const.SUPPORT_BUNDLE

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.SUPPORT_BUNDLE,
                                     help='Create, list or delete support bundle.')
        sbparser.add_argument('action', help='action',
                              choices=['create', 'list', 'delete'])
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=SupportBundleCommand)


class EmailConfigCommand(Command):
    """ Contains functionality to handle Email Configuration """

    _name = const.EMAIL_CONFIGURATION

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.EMAIL_CONFIGURATION,
                                     help='Perform | reset  email configuration, \
                                     show, subscribe or unsubscribe for email \
                                     alerts.')
        sbparser.add_argument('action', help='action',
                              choices=['config', 'reset', 'show', 'subscribe',
                                       'unsubscribe'])
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=EmailConfigCommand)


class AlertsCommand(Command):
    """ Contains functionality to handle Alerts """

    _name = const.ALERTS_COMMAND
    _method = {'show': 'get', 'acknowledge': 'patch'}
    _headers = const.ALERTS_CLI_HEADERS
    _filter = const.ALERTS_COMMAND

    def __init__(self, action, options, args):
        super().__init__(action, options, args)
        self._method = AlertsCommand._method

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.ALERTS_COMMAND,
                                     help='Show | Acknowledge system alerts')
        sbparser.add_argument('action', help='Action',
                              choices=['show', 'acknowledge'])
        sbparser.add_argument('-d', help='Seconds', dest='duration', nargs='?',
                              default="60s")
        sbparser.add_argument('-c', help='No. of Alerts', dest='limit',
                              nargs='?', default=1000)
        sbparser.add_argument('-a', help='Display All Alerts', dest='all',
                              action='store_const', default='false', const='true')
        sbparser.add_argument('-f', help='Format', dest='format', nargs='?',
                              default='table', choices=['json', 'xml', 'table'])
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=AlertsCommand)

    def validate_command(self):
        if self._action == 'acknowledge':
            if len(self.args) != 2:
                raise AttributeError(
                    'For "acknowledge" action you must specify "id" and "comment" arguments')
            try:
                int(self.args[0])
            except ValueError:
                raise CsmError(errno.EINVAL,
                               f'"id" argument must be integer, got {self.args[0]} instead')
            if not isinstance(self.args[1], str):
                raise CsmError(errno.EINVAL,
                               f'"comment" argument must be string, got {self.args[1]} instead')

    def update_options(self):
        if self._action == 'acknowledge':
            # To avoid this we need to restructure argument addition process
            self._options.clear()

            self._options['alert_id'] = self.args[0]
            self._options['comment'] = self.args[1]
