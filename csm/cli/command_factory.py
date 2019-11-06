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
import os
from csm.core.blogic import const
from csm.common.payload import Json
from csm.cli.commands import CommandParser


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # todo:  Need to Modify the changes for Fetching Error Messages from config file
        self.print_usage(sys.stderr)
        self.exit(2, f'Error: {message.capitalize()}\n')


class CommandFactory(object):
    """
    Factory for representing and creating command objects using
    a generic skeleton.
    """

    @staticmethod
    def get_command(argv):
        """
        Parse the command line as per the syntax and retuns
        returns command representing the command line.
        """
        # Todo: Fetch Messages from Message ile for localization. & implement Marshmallow for Schema Validation.
        commands = os.listdir(const.COMMAND_DIRECTORY)
        commands = [command.split(".json")[0] for command in commands]
        commands.remove(const.CSM_SETUP_CMD)
        parser = ArgumentParser(description='CSM CLI command')
        subparsers = parser.add_subparsers(metavar=commands)
        if not argv:
            argv = ['-h']
        if argv[0] != '-h' and argv[0] in commands:
            cmd_obj = CommandParser(
                Json(os.path.join(const.COMMAND_DIRECTORY, f"{argv[0]}.json")).load())
            cmd_obj.handle_main_parse(subparsers)
        namespace = parser.parse_args(argv)
        sys_module = sys.modules[__name__]
        try:
            for attr in ['command', 'action', 'args']:
                setattr(sys_module, attr, getattr(namespace, attr))
                delattr(namespace, attr)
            return command(action, vars(namespace), args)
        except AttributeError:
            sys.stderr.write(f"Please See Usage Below. \n")
            argv.append('-h')
            parser.parse_args(argv)
