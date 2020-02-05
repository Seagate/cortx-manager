#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          csm_init.py
 Description:       Entry point for CSM_INIT

 Creation Date:     23/08/2019
 Author:            Ajay Paratmandali

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
import argparse
import traceback
import time

class CsmSetupCommand:
    """
        Provide cli to setup csm. Create user for csm to allow basic
        permission like log, bundle path.
    """
    def __init__(self, argv):
        ''' Check csm setup command and initialize '''
        Log.init(service_name = "csm_setup")
        self._args = argv
        self._args[0] = 'csm_setup'
        self._validate()
        Conf.init()

    def _validate(self):
        ''' Validate setup command '''
        if len(self._args) < 2:
            raise Exception('Usage: csm_setup -h')

    def _get_command(self):
        ''' Parse csm setup command '''
        parser = argparse.ArgumentParser(description='CSM Setup CLI', usage='')
        subparsers = parser.add_subparsers()
        cmd_obj = CommandParser(Json(const.CSM_SETUP_FILE).load())
        cmd_obj.handle_main_parse(subparsers)
        namespace = parser.parse_args(self._args)
        sys_module = sys.modules[__name__]
        for attr in ['command', 'action', 'args']:
            setattr(sys_module, attr, getattr(namespace, attr))
            delattr(namespace, attr)
        return command(action, vars(namespace), args)

    def process(self):
        ''' Parse args for csm_setup and execute cmd to print output '''
        self._cmd = self._get_command()
        self._response = None
        self._request = Request(self._cmd._name, self._cmd.args, self._cmd.options)
        self.process_request(self._process_response)
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)
        if self._response.rc() != 0:
            raise CsmError(self._response.rc(), "%s" %self._response.output())
        return self._response.output()

    def process_request(self, callback=None):
        Log.debug('command=%s action=%s args=%s options=%s' %(self._cmd.name,
            self._request.action, self._request.args, self._request.options))
        self._providers = SetupProvider()
        return self._providers.process_request(self._request, callback)

    def _process_response(self, response):
        self._response = response

if __name__ == '__main__':
    cli_path = os.path.realpath(sys.argv[0])
    sys.path.append(os.path.join(os.path.dirname(cli_path), '..', '..'))

    from csm.common.log import Log
    from csm.common.conf import Conf
    from csm.common.payload import *
    from csm.common.errors import CsmError
    from csm.cli.command import CommandParser
    from csm.core.blogic import const
    from csm.core.providers.providers import Request, Response
    from csm.core.providers.setup_provider import SetupProvider

    try:
        csm_setup = CsmSetupCommand(sys.argv)
        sys.stdout.write('%s\n' % csm_setup.process())
    except Exception as exception:
        Log.error(traceback.format_exc())
        sys.stderr.write('csm_setup command failed: %s\n' %exception)
