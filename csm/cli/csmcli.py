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

from csm.cli.command_factory import CommandFactory
from csm.core.api.api_client import CsmApiClient
from csm.common.log import Log
from csm.common.conf import Conf
from csm.common.payload import *
from csm.core.blogic import const

def main(argv):
    """
    Parse command line to obtain command structure. Execute the CLI
    command and print the result back to the terminal.
    """
    cli_path = os.path.realpath(argv[0])
    sys.path.append(os.path.join(os.path.dirname(cli_path), '..', '..'))

    Log.init("csm", "/var/log/csm")
    try:
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))

        command = CommandFactory.get_command(argv[1:])
        # TODO - Use Factory Method for Api Client
        client = CsmApiClient()
        response = client.call(command)
        rc = response.rc()
        if rc != 0:
            sys.stdout.write('error(%d): ' %rc)
        sys.stdout.write('%s\n' %response.output())
        return rc

    except Exception as exception:
        sys.stderr.write('%s\n' %exception)
        Log.error(traceback.format_exc())
        # TODO - Extract rc from exception
        return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
