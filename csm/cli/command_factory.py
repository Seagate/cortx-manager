"""
 ****************************************************************************
 Filename:          command_factory.py
 Description:       CLI Command Factory
                    Converts RAS CLI command line to command structure

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

import argparse
import sys
from csm.cli.commands import SupportBundleCommand
from csm.cli.commands import EmailConfigCommand
from csm.cli.commands import AlertsCommand


class CommandFactory(object):
    """
    Factory for representing and creating command objects using
    a generic skeleton.
    """

    commands = {SupportBundleCommand, EmailConfigCommand, AlertsCommand}

    @staticmethod
    def get_command(argv):
        """
        Parse the command line as per the syntax and retuns
        returns command representing the command line.
        """

        parser = argparse.ArgumentParser(description='RAS CLI command')
        subparsers = parser.add_subparsers()

        for each_command in CommandFactory.commands:
            each_command.add_args(subparsers)

        namespace = parser.parse_args(argv)
        sys_module = sys.modules[__name__]
        for attr in ['command', 'action', 'args']:
            setattr(sys_module, attr, getattr(namespace, attr))
            delattr(namespace, attr)
        return command(action, vars(namespace), args)
