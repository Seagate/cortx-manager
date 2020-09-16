# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import argparse
import os
import sys

from csm.cli.command import CommandParser
from csm.common.payload import Json
from csm.core.blogic import const


class ArgumentParser(argparse.ArgumentParser):
    """Overwritten ArgumentParser class for internal purposes"""
    def error(self, message):
        # TODO:  Need to Modify the changes for Fetching Error Messages from config file
        self.print_usage(sys.stderr)
        self.exit(2, f'Error: {message.capitalize()}\n')


class CommandFactory:
    """Factory for representing and creating command objects using a generic skeleton."""
    @staticmethod
    def get_command(argv, permissions):
        """
        Parse the command line as per the syntax and returns command representing the command line.
        """

        # TODO: Fetch Messages from Message file for localization.
        # TODO: implement Marshmallow for Schema Validation.
        # TODO: Add Changes to Exclude Some Commands From Help Section.
        if len(argv) <= 1:
            argv.append("-h")
        commands = os.listdir(const.COMMAND_DIRECTORY)
        commands = [command.split(".json")[0] for command in commands
                    if command.split(".json")[0] not in const.EXCLUDED_COMMANDS]
        if permissions:
            # common commands both in commands and permissions key list
            commands = [command for command in commands if command in permissions.keys()]
        parser = ArgumentParser(description='Cortx cli commands')
        metavar = set(commands).difference(set(const.HIDDEN_COMMANDS))
        subparsers = parser.add_subparsers(metavar=metavar)
        if argv[0] in commands:
            # get command json file and filter only allowed first level sub_command
            # create filter_permission_json
            cmd_from_file = Json(os.path.join(const.COMMAND_DIRECTORY, f"{argv[0]}.json")).load()
            cmd_obj = CommandParser(cmd_from_file, permissions.get(argv[0], {}))
            cmd_obj.handle_main_parse(subparsers)
        namespace = parser.parse_args(argv)

        CommandFactory.edit_arguments(namespace)

        sys_module = sys.modules[__name__]
        for attr in ['command', 'action', 'args']:
            setattr(sys_module, attr, getattr(namespace, attr))
            delattr(namespace, attr)
        return command(action, vars(namespace), args)  # pylint: disable=undefined-variable

    @staticmethod
    def edit_arguments(namespace):
        # temporary solution till user create api is not fixed
        # remove when fixed
        if namespace.action == 'users' and namespace.sub_command_name == 'create':
            namespace.roles = [namespace.roles]
