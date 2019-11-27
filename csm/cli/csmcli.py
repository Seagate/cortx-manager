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


def main(argv):
    """
    Parse command line to obtain command structure. Execute the CLI
    command and print the result back to the terminal.
    """

    Log.init("csm", "/var/log/csm")
    try:
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))

        command = CommandFactory.get_command(argv[1:])
        if command.need_confirmation:
            res = get_quest_answer(" ".join((command.name, command.sub_command_name)))
            if res is False:
                return 0

        if not command.comm.get("type", "") in const.CLI_SUPPORTED_PROTOCOLS:
            raise Exception(
                f"Invalid Communication Protocol {command.comm.get('type', '')} Selected."
            )
        csm_agent_url = f"{const.CSM_AGENT_BASE_URL}{const.CSM_AGENT_HOST}:{const.CSM_AGENT_PORT}/api"
        client = CsmRestClient(csm_agent_url)

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(client.call(command))
        command.process_response(out=sys.stdout, err=sys.stderr,
                                 response=response)
    except Exception as exception:
        sys.stderr.write(str(exception) + '\n')
        Log.error(traceback.format_exc())
        # TODO - Extract rc from exception
        return 1


if __name__ == '__main__':
    cli_path = os.path.realpath(sys.argv[0])
    sys.path.append(os.path.join(os.path.dirname(cli_path), '..', '..'))

    from csm.cli.command_factory import CommandFactory
    from csm.cli.csm_client import CsmRestClient, Output
    from csm.common.log import Log
    from csm.common.conf import Conf
    from csm.common.payload import *
    from csm.core.blogic import const

    sys.exit(main(sys.argv))
