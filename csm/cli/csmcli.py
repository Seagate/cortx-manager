#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          main.py
 Description:       Entry point for RAS CLI

 Creation Date:     31/05/2018
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
import os
import traceback
import asyncio
from getpass import getpass
from cmd import Cmd
import pathlib

class Terminal:
    @staticmethod
    def get_quest_answer(name: str) -> bool:
        """
        Asks user user a question using stdout
        Returns True or False, depending on an answer

        :param quest: question string
        :return: True or False depending on user input
        """

        while True:
            # Postive answer is default
            sys.stdout.write(f'Are you sure you want to perform "{name}" command? [Y/n] ')

            usr_input = input().lower()
            if usr_input in ['y', 'yes', '']:
                return True
            elif usr_input in ['n', 'no']:
                return False
            else:
                sys.stdout.write("Please answer with 'yes' or 'no'\n")

    @staticmethod
    def logout_alert(is_logged_out: bool):
        if is_logged_out:
            sys.stdout.write('Successfully logged out\n')
        else:
            Log.error(traceback.format_exc())
            sys.stderr('Logout failed\n')

    @staticmethod
    def get_password(value, confirm_pass_flag=True):
        """
        Fetches the Password from Terminal in Non-Echo Mode.
        :return:
        """
        password = value or getpass(prompt="Password: ")
        if confirm_pass_flag:
            confirm_password = getpass(prompt="Confirm Password: ")
            if not confirm_password==password:  
                raise InvalidRequest("Password do not match.")    
        return password



class CsmCli(Cmd):
    def __init__(self, args):
        super(CsmCli, self).__init__(stdout=sys.stdout)
        self.intro = const.INTERACTIVE_SHELL_HEADER
        self.prompt = const.CLI_PROMPT
        if len(args) > 1:
            self.args = args[1:]
        else:
            self.args = "help"
        self.loop = asyncio.get_event_loop()
        self.rest_client = None
        self.username = ""
        self._permissions = Json(const.CLI_DEFAULTS_ROLES).load()

    def preloop(self):
        """
        Initialize Log for CSM CLI and Set the API for Rest API
        :return:
        """
        #Set Logger
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
        Log.init("csm_cli",
             syslog_server=Conf.get(const.CSM_GLOBAL_INDEX, "Log.syslog_server"),
             syslog_port=Conf.get(const.CSM_GLOBAL_INDEX, "Log.syslog_port"),
             backup_count=Conf.get(const.CSM_GLOBAL_INDEX, "Log.total_files"),
             file_size_in_mb=Conf.get(const.CSM_GLOBAL_INDEX, "Log.file_size"),
             log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path"),
             level=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_level"))
        #Set Rest API for CLI
        csm_agent_port = Conf.get(const.CSM_GLOBAL_INDEX,'CSMCLI.csm_agent_port')
        csm_agent_host = Conf.get(const.CSM_GLOBAL_INDEX,'CSMCLI.csm_agent_host')
        csm_agent_base_url = Conf.get(const.CSM_GLOBAL_INDEX, 'CSMCLI.csm_agent_base_url')
        csm_agent_url = f"{csm_agent_base_url}{csm_agent_host}:{csm_agent_port}/api"
        self.rest_client = CsmRestClient(csm_agent_url)
        self.check_auth_required()

    def check_auth_required(self):
        if self.args[0] not in const.NO_AUTH_COMMANDS:
            self.login()
        else:
            self.default(self.args)
            self.do_exit()

    def emptyline(self):
        pass

    def login(self):
        """
        Function Takes Responsibility for Login into CSM CLI.
        :return:None
        """
        try:
            self.username = input('Username: ').strip()
            Log.debug(f"{self.username} attempted to Login.")
            if self.username:
                password = getpass(prompt="Password: ")
                is_logged_in = self.loop.run_until_complete(self.rest_client.login(
                    self.username, password))
                if not is_logged_in:
                    self.do_exit("Server authentication check failed.")
                Log.info(f"{self.username}: Logged In.")
                response = self.loop.run_until_complete(self.rest_client.permissions())
                if response:
                    self._permissions.update(response)
        except CsmError as e:
            Log.error(f"{self.username}:{e}")
        except KeyboardInterrupt:
            self.do_exit()
        except Exception as e:
            Log.critical(f"{self.username}:{e}")
            self.do_exit(f"Some Error Occurred.\n")

    def precmd(self, command):
        """
        Pre-Process the Entered Command.
        :param command: Command Entered by User.
        :return:
        """
        if command.strip():
            self.args = [x.strip() for x in command.split(" ")]
        return command

    def process_direct_command(self, command):
        obj = CsmDirectClient()
        response = self.loop.run_until_complete(obj.call(command))
        if response:
            command.process_response(out=sys.stdout, err=sys.stderr,
                                 response=response)

    def process_rest_command(self, command):
        response, _ = self.loop.run_until_complete(self.rest_client.call(command))
        command.process_response(out=sys.stdout, err=sys.stderr,
                                 response=response)

    def default(self, cmd):
        """
        Default Function for Initializing each Command.
        :param cmd: Command Entered by User :type:str
        :return:
        """
        try:
            command = CommandFactory.get_command(self.args, self._permissions)
            if command.need_confirmation:
                res = Terminal.get_quest_answer(" ".join((command.name,
                                                    command.sub_command_name)))
            channel_name = f"""process_{command.comm.get("type", "")}_command"""
            if not hasattr(self, channel_name):
                err_str = f"Invalid Communication Protocol {command.comm.get('type','')} Selected."
                Log.error(f"{self.username}:{err_str}")
                sys.stderr(err_str)
            getattr(self, channel_name)(command)
            Log.info(f"{self.username}: {cmd}: Command Executed")
        except CsmError as e:
            Log.error(f"{self.username}:{e}")
        except SystemExit:
            Log.debug(f"{self.username}: Command Executed System Exit")
        except KeyboardInterrupt:
            Log.debug(f"{self.username}: Stopped via Keyboard Interrupt.")
            self.do_exit()
        except Exception as e:
            Log.critical(f"{self.username}:{e}")
            self.do_exit("Some Error Occurred.\n Please try Re-Login")

    def do_exit(self, args=""):
        """
        This Function Exits the Interactive Shell whenever "EXIT" or "QUIT" or
        Keyboard Interrupts are called.
        :return:
        """
        if args:
            sys.stdout.write(f"{args}\n")
        if self.rest_client.has_open_session():
            Log.info(f"{self.username}: Logged Out")
            is_logged_out = self.loop.run_until_complete(self.rest_client.logout())
            Terminal.logout_alert(is_logged_out)
            assert isinstance(is_logged_out, bool)
        Log.info(f"{self.username}: Logged Out")
        sys.exit()

if __name__ == '__main__':
    cli_path = os.path.realpath(sys.argv[0])
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    from csm.cli.command_factory import CommandFactory, ArgumentParser
    from csm.cli.csm_client import CsmRestClient, CsmDirectClient
    from csm.common.log import Log
    from csm.common.conf import Conf
    from csm.common.errors import CsmError
    from csm.common.payload import *
    from csm.core.blogic import const
    from csm.common.errors import InvalidRequest

    CsmCli(sys.argv).cmdloop()
