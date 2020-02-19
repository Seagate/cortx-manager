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

import argparse
import getpass
import json
from typing import Dict, Any
from copy import deepcopy
from dict2xml import dict2xml
from prettytable import PrettyTable
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.cli.csmcli import Terminal

class Command:
    """CLI Command Base Class"""

    def __init__(self, name, options, args):
        self._method = options['comm']['method']
        self._target = options['comm']['target']
        self._comm = options['comm']
        self._options = options
        self._args = args
        self._name = name
        self._output = options["output"]
        self._need_confirmation = options['need_confirmation']
        self._sub_command_name = options['sub_command_name']

    @property
    def name(self):
        return self._name

    @property
    def options(self):
        return self._options

    @property
    def args(self):
        return self._args

    @property
    def method(self):
        return self._method

    @property
    def target(self):
        return self._target

    @property
    def comm(self):
        return self._comm

    @property
    def need_confirmation(self):
        return self._need_confirmation

    @property
    def sub_command_name(self):
        return self._sub_command_name

    def process_response(self, response, out, err):
        """Process Response as per display method in format else normal display"""
        output_obj = Output(self, response)
        return output_obj.dump(out, err, **self._output,
                               output_type=self._options.get('format',
                                                             "success"))


class Validatiors:
    """CLI Validatiors Class"""
    @staticmethod
    def positive_int(value):
        try:
            if int(value) > -1:
                return int(value)
            raise argparse.ArgumentError("Value Must be Positive Integer")
        except ValueError:
            raise argparse.ArgumentError("Value Must be Positive Integer")

class CommandParser:
    """
    This Class Parses the Commands from the dictionary object
    """

    def __init__(self, cmd_data: Dict):
        self.command = cmd_data
        self._communication_obj = {}

    def handle_main_parse(self, subparsers):
        """
        This Function Handles the Parsing of Single-Level and Multi-Level
        Command Arguments
        :param subparsers: argparser Object
        :return:
        """
        if "sub_commands" in self.command:
            self.handle_subparsers(subparsers, self.command,
                                   self.command["name"])
        elif "args" in self.command:
            self.add_args(self.command, subparsers, self.command["name"])

    def handle_subparsers(self, sub_parser, data: Dict, name):
        """
        This Function will handle multiple sub-parsing commands
        :param sub_parser: Arg-parser Object
        :param data: Data for parsing the commands :type: Dict
        :param name: Name of the Command :type:Str
        :return: None
        """
        arg_parser = sub_parser.add_parser(data['name'],
                                           help=data['description'])
        parser = arg_parser.add_subparsers()
        for each_data in data['sub_commands']:
            self.add_args(each_data, parser, name)

    def handle_comm(self, each_args):
        """
        This method will handle the rest params and create the necessary object.
        :param each_args:
        :return:
        """
        if each_args.get("params", False):
            each_args.pop("params")
            self._communication_obj['params'][
                each_args.get('dest', None) or each_args.get('flag')] = ""
        if each_args.get("json", False):
            each_args.pop("json")
            self._communication_obj['json'][
                each_args.get('dest', None) or each_args.get('flag')] = ""

    def add_args(self, sub_command: Dict, parser: Any, name):
        """
        This Function will add the cmd_args from the Json to the structure.
        :param sub_command: Action for which the command needs to be added
        :type: str
        :param parser: ArgParse Parser Object :type: Any
        :param name: Name of the Command :type: str
        :return: None
        """
        sub_parser = parser.add_parser(sub_command["name"],
                                       help=sub_command["description"])
        # Check if the command has any arguments.
        if "args" in sub_command:
            self._communication_obj.update(sub_command['comm'])
            self._communication_obj['params'] = {}
            self._communication_obj['json'] = {}
            for each_args in sub_command["args"]:
                if each_args.get("type", None):
                    each_args["type"] = eval(each_args["type"])
                if each_args.get("suppress_help", False):
                    each_args.pop("suppress_help")
                    each_args['help'] = argparse.SUPPRESS
                self.handle_comm(each_args)
                flag = each_args.pop("flag")
                sub_parser.add_argument(flag, **each_args)
            sub_parser.set_defaults(command=Command,
                                    action=deepcopy(name),
                                    comm=deepcopy(self._communication_obj),
                                    output=deepcopy(sub_command.get('output', {})),
                                    need_confirmation=sub_command.get('need_confirmation', False),
                                    sub_command_name=sub_command.get('name'))

        # Check if the command has any Commands.
        elif "sub_commands" in sub_command:
            for each_command in sub_command['sub_commands']:
                self.handle_subparsers(sub_parser, each_command, name)

class Output:
    """CLI Response Display Class"""
    def __init__(self, command, response):
        self.command = command
        self.rc = response.rc()
        self.output = response.output()

    def dump(self, out, err, output_type, **kwargs) -> None:
        """Dump the Output on CLI"""
        # Todo: Need to fetch the response messages from a file for localization.
        # TODO: Check 201 response code also for creation requests.
        if self.rc not in  (200, CSM_OPERATION_SUCESSFUL) :
            errstr = Output.error(self.rc, kwargs.get("error"),
                                  self.output)
            err.write(f"{errstr}\n" or "")
            return None
        elif output_type:
            output = getattr(Output, f'dump_{output_type}')(self.output,
                                                            **kwargs)
            out.write(f"{output}\n")

    @staticmethod
    def dump_success(output: Any, **kwargs):
        """
        Accepts String as Output and Returns the Same.
        :param output: Output String
        :return:
        """
        return str(kwargs.get("success", output))

    @staticmethod
    def error(rc: int, message: str, stacktrace) -> str:
        """Format for Error message"""
        if message:
            return f'error({rc}): {message}\n'
        return f"error({rc}): Error:- {stacktrace.get('message')}"

    @staticmethod
    def dump_table(data: Any, table: Dict, **kwargs: Dict) -> str:
        """Format for Table Data"""
        table_obj = PrettyTable()
        table_obj.field_names = table["headers"].values()
        if table.get("filters", False):
            for each_row in data[table["filters"]]:
                table_obj.add_row(
                    [each_row.get(x) for x in table["headers"].keys()])
        else:
            table_obj.add_row([data.get(x) for x in table["headers"].keys()])
        return "{0}".format(table_obj)

    @staticmethod
    def dump_xml(data, **kwargs: Dict) -> str:
        """Format for XML Data"""
        return dict2xml(data)

    @staticmethod
    def dump_json(data, **kwargs: Dict) -> str:
        """Format for Json Data"""
        return json.dumps(data, indent=4, sort_keys=True)
