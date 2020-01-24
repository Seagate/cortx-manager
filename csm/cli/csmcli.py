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
from csm.common.errors import InvalidRequest


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
            sys.stdout.write('Successfully logged out')
        else:
            Log.error(traceback.format_exc())
            sys.stderr('Logout failed')

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

def main(argv):
    """
    Parse command line to obtain command structure. Execute the CLI
    command and print the result back to the terminal.
    """

    try:
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
        Log.init("csm", Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path"),
                  Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_level"),
                  Conf.get(const.CSM_GLOBAL_INDEX, "Log.file_size"),
                  Conf.get(const.CSM_GLOBAL_INDEX, "Log.total_files"))
        csm_agent_port = Conf.get(const.CSM_GLOBAL_INDEX,
                        'CSMCLI.csm_agent_port') or const.CSM_AGENT_PORT
        csm_agent_host = Conf.get(const.CSM_GLOBAL_INDEX,
                        'CSMCLI.csm_agent_host') or const.CSM_AGENT_HOST
        csm_agent_base_url = Conf.get(const.CSM_GLOBAL_INDEX,
                        'CSMCLI.csm_agent_base_url') or const.CSM_AGENT_BASE_URL
        csm_agent_url = f"{csm_agent_base_url}{csm_agent_host}:{csm_agent_port}/api"
        rest_client = CsmRestClient(csm_agent_url)
        loop = asyncio.get_event_loop()

        start_parser = ArgumentParser(description='CSM CLI command')
        start_parser.add_argument('--username', required=False)
        start_parser.add_argument('--command-file', required=False)

        assert len(argv) >= 1
        username = None
        command_file = None
        if len(argv) == 1:
            username = input('Username: ').strip()
        else:
            args = vars(start_parser.parse_args(argv[1:]))
            username = args.get('username')
            command_file = args.get('command-file')
        if username:
            password = getpass(prompt="Password: ")
            is_logged_in = loop.run_until_complete(rest_client.login(username, password))
            if is_logged_in:
                sys.stdout.write(f'You\'ve logged in as {username}\n')
            else:
                raise Exception("Server authentication check failed")
        else:
            sys.stdout.write('You\'ve entered csmcli in unathorized mode\n')
        if command_file:
            raise Exception("Command file option is not avaliable for now")

        while True:
            try:
                args = input('csmcli> ').split()
                if len(args) == 0:
                    continue
                elif len(args) == 1:
                    if args[0] in ['exit', 'logout']:
                        if rest_client.has_open_session():
                            is_logged_out = loop.run_until_complete(rest_client.logout())
                            Terminal.logout_alert(is_logged_out)
                            assert isinstance(is_logged_out, bool)
                            return int(not is_logged_out)
                        else:
                            return 0
                command = CommandFactory.get_command(args)
                if command.need_confirmation:
                    res = Terminal.get_quest_answer(
                        " ".join((command.name, command.sub_command_name)))
                    if res is False:
                        continue
                if not command.comm.get("type", "") in const.CLI_SUPPORTED_PROTOCOLS:
                    raise Exception(
                        f"Invalid Communication Protocol {command.comm.get('type', '')} Selected."
                    )
                response, _ = loop.run_until_complete(rest_client.call(command))
                command.process_response(out=sys.stdout, err=sys.stderr,
                                         response=response)
            except SystemExit:
                # Argparse thorws SystemExit on "help" and "show version" actions, so we just ignore it
                pass
            except Exception as exception:
                sys.stderr.write(str(exception) + '\n')
                Log.critical(traceback.format_exc())
    except KeyboardInterrupt:
        if rest_client.has_open_session():
            is_logged_out = loop.run_until_complete(rest_client.logout())
            Terminal.logout_alert(is_logged_out)
            assert isinstance(is_logged_out, bool)
            return int(not is_logged_out)
    except Exception as exception:
        sys.stderr.write(str(exception) + '\n')
        Log.critical(traceback.format_exc())
        # TODO - Extract rc from exception
        return 1
    finally:
        sys.stdout.write('\n')


if __name__ == '__main__':
    cli_path = os.path.realpath(sys.argv[0])
    sys.path.append(os.path.join(os.path.dirname(cli_path), '..', '..'))

    from csm.cli.command_factory import CommandFactory, ArgumentParser
    from csm.cli.csm_client import CsmRestClient
    from csm.cli.command import Output
    from csm.common.log import Log
    from csm.common.conf import Conf
    from csm.common.payload import *
    from csm.core.blogic import const

    sys.exit(main(sys.argv))
