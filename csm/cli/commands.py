#!/usr/bin/python

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

import abc, argparse
from csm.common import const

class Command(object):
    """ Base class for all commands supported by RAS CLI """

    def __init__(self, args):
        self._args = args

    def action(self):
        return self._args.action

    def args(self):
        return self._args

class InitCommand(Command):
    """ Contains funtionality to initialization CSM """

    def __init__(self, args):
        super(InitCommand, self).__init__(args)

    def name(self):
        return const.CSM_INIT_CMD

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.CSM_INIT_CMD, help='Initialize csm component.')
        sbparser.add_argument('action', help='action', choices=const.CSM_INIT_ACTIONS)
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=InitCommand)

class SupportBundleCommand(Command):
    """ Contains funtionality to handle support bundle """

    def __init__(self, args):
        super(SupportBundleCommand, self).__init__(args)

    def name(self):
        return const.SUPPORT_BUNDLE

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.SUPPORT_BUNDLE, help='Create, list or delete support bundle.')
        sbparser.add_argument('action', help='action', choices=['create', 'list', 'delete'])
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=SupportBundleCommand)

class EmailConfigCommand(Command):
    """ Contains funtionality to handle Email Configuration """

    def __init__(self, args):
        super(EmailConfigCommand, self).__init__(args)

    def name(self):
        return const.EMAIL_CONFIGURATION

    @staticmethod
    def add_args(parser):
        sbparser = parser.add_parser(const.EMAIL_CONFIGURATION,
            help='Perform | reset  email configuration, show, subscribe or unsubscribe for email alerts.')
        sbparser.add_argument('action', help='action', choices=['config', 'reset', 'show', 'subscribe', 'unsubscribe'])
        sbparser.add_argument('args', nargs='*', default=[], help='bar help')
        sbparser.set_defaults(command=EmailConfigCommand)
