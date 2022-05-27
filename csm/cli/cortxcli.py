#!/usr/bin/env python3

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

import sys
import os
import asyncio
import shlex
from getpass import getpass
from cmd import Cmd
import pathlib

class CortxCli(Cmd):
    """CORTX CLI."""

    def __init__(self, args):
        """Initialize CORTX CLI."""
        super(CortxCli, self).__init__()
        self.intro = const.INTERACTIVE_SHELL_HEADER
        self.prompt = const.CLI_PROMPT
        if len(args) > 1:
            self.args = args[1:]
        else:
            self.args = "help"
        self.loop = asyncio.get_event_loop()
        self.rest_client = None
        self.username = ""
        self._session_token = None
        self.headers = {}
        self._permissions = Json(const.CLI_DEFAULTS_ROLES).load()
        self.some_error_occured = 'Some error occurred.\nPlease try login again.\n'
        self.session_expired_error = 'Session expired.\nPlease try login again.\n'
        self.server_down = 'CSM service is not found.\nPlease check whether CSM is running.\n'


    def preloop(self):
        """
        Initialize Log for CSM CLI and Set the API for Rest API
        :return:
        """

        #Set Logger
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, f"yaml://{const.CSM_CONF}")
        backup_count = Conf.get(const.CSM_GLOBAL_INDEX, "Log>total_files")
        file_size_in_mb = Conf.get(const.CSM_GLOBAL_INDEX, "Log>file_size")
        Log.init("cortxcli",
             backup_count = int(backup_count) if backup_count else None,
             file_size_in_mb = int(file_size_in_mb) if file_size_in_mb else None,
             log_path = Conf.get(const.CSM_GLOBAL_INDEX, const.LOG_PATH),
             level = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_level"))
        #Set Rest API for CLI
        csm_agent_port = Conf.get(const.CSM_GLOBAL_INDEX,'CSM_SERVICE>CSM_AGENT>port')
        csm_agent_host = Conf.get(const.CSM_GLOBAL_INDEX,'CSM_SERVICE>CSM_AGENT>host')
        csm_agent_base_url = Conf.get(const.CSM_GLOBAL_INDEX,'CSM_SERVICE>CSM_AGENT>base_url')
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
                self._session_token = self.loop.run_until_complete(self.rest_client.login(
                    self.username, password))
                if not self._session_token:
                    self.do_exit("Server authentication check failed.")
                self.headers = {'Authorization': f'Bearer {self._session_token}'}
                Log.info(f"{self.username}: Logged in.")
                response = self.loop.run_until_complete(self.rest_client.permissions(self.headers))
                if response:
                    self._permissions.update(response)
            else:
                self.do_exit("Username wasn't provided.")
        except CsmError as e:
            Log.error(f"{self.username}:{e}")
        except KeyboardInterrupt:
            self.do_exit()
        except Exception as e:
            Log.critical(f"{self.username}:{e}")
            self.do_exit(self.some_error_occured)

    def precmd(self, command):
        """
        Pre-Process the Entered Command.
        :param command: Command Entered by User.
        :return:
        """
        if command.strip():
            self.args = shlex.split(command)
        return command

    def process_direct_command(self, command):
        obj = CliClient()
        response = self.loop.run_until_complete(obj.call(command))
        if response:
            command.process_response(out=sys.stdout, err=sys.stderr,
                                 response=response)

    def process_rest_command(self, command):
        response, _ = self.loop.run_until_complete(self.rest_client.call(command,
                                                                 self.headers))
        command.process_response(out=sys.stdout, err=sys.stderr,
                                 response=response)

    def default(self, cmd):
        """
        Default Function for Initializing each Command.
        :param cmd: Command Entered by User :type:str
        :return:
        """
        try:
            Log.debug(f"{self.username}: {cmd}")
            command = CommandFactory.get_command(self.args,
                                                self._permissions,
                                                const.COMMAND_DIRECTORY,
                                                const.EXCLUDED_COMMANDS,
                                                const.HIDDEN_COMMANDS)
            if command.need_confirmation:
                res = Terminal.get_quest_answer(" ".join((command.name,
                                                    command.sub_command_name)))
                if not res:
                    return None
            channel_name = f"""process_{command.comm.get("type", "")}_command"""
            if not hasattr(self, channel_name):
                err_str = f"Invalid communication protocol {command.comm.get('type','')} selected."
                Log.error(f"{self.username}:{err_str}")
                sys.stderr.write(err_str)
            getattr(self, channel_name)(command)
            Log.info(f"{self.username}: {cmd}: Command executed")
        except CsmUnauthorizedError as e:
            Log.error(f"{self.username}:{e}")
            # Setting session token to None cause it's already expired
            self._session_token = None
            self.do_exit(self.session_expired_error)
        except CsmServiceNotAvailable as e:
            Log.error(f"{self.username}:{e}")
            self._session_token = None
            self.do_exit(self.server_down)
        except CsmError as e:
            Log.error(f"{self.username}:{e}")
        except VError as ve:
            sys.stdout.write(f"{ve.desc}\n")
            Log.error(f"{self.username}:{ve}")
        except SystemExit:
            Log.debug(f"{self.username}: Command executed system exit")
        except KeyboardInterrupt:
            Log.debug(f"{self.username}: Stopped via keyboard interrupt.")
            self.do_exit()
        except Exception as e:
            Log.critical(f"{self.username}:{e}")
            self.do_exit(self.some_error_occured)

    def do_exit(self, args=""):
        """
        This Function Exits the Interactive Shell whenever "EXIT" or "QUIT" or
        Keyboard Interrupts are called.
        :return:
        """
        if args:
            sys.stdout.write(f"{args}\n")
        if self._session_token:
            is_logged_out = self.loop.run_until_complete(self.rest_client.logout(
                self.headers))
            self.headers = {}
            Terminal.logout_alert(True)
            assert isinstance(is_logged_out, bool)
        Log.info(f"{self.username}: Logged out")
        sys.exit()

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..'))
    from cortx.utils.cli_framework.command_factory import CommandFactory
    from csm.cli.csm_client import CsmRestClient
    from cortx.utils.cli_framework.client import CliClient
    from cortx.utils.log import Log
    from cortx.utils.conf_store.conf_store import Conf
    from cortx.utils.cli_framework.terminal import Terminal
    from csm.common.errors import CsmError, CsmUnauthorizedError, CsmServiceNotAvailable
    from csm.common.payload import *
    from csm.core.blogic import const
    from csm.common.errors import InvalidRequest
    from csm.common.conf import Security
    from cortx.utils.validator.error import VError
    try:
        CortxCli(sys.argv).cmdloop()
    except KeyboardInterrupt:
        Log.debug("Stopped via keyboard interrupt.")
        sys.stdout.write("\n")
    except InvalidRequest as e:
        raise InvalidRequest(f"{e}")
    except Exception as e:
        Log.critical(f"{e}")
        sys.stderr.write('Some error occurred.\nPlease try login again.\n')
