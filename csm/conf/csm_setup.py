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

class CsmSetup:
    """
        Provide cli to setup csm. Create user for csm to allow basic
        permission like log, bundle path.
    """
    def __init__(self, argv):
        Log.init("csm_setup", "/var/log/csm")
        self._args = argv[1:]
        self._args.insert(0, 'csm_setup')
        Conf.init()
        self._load_conf()
        self._config_cluster()

    def _load_conf(self):
        ''' Load all configuration file and through error if file is missing '''
        if not os.path.exists(const.CSM_CONF):
            raise CsmError(-1, "%s file is missing for csm setup" %const.CSM_CONF)
        if not os.path.exists(const.INVENTORY_FILE):
            raise CsmError(-1, "%s file is missing for csm setup" %const.INVENTORY_FILE)
        if not os.path.exists(const.COMPONENTS_CONF):
            raise CsmError(-1, "%s file is missing for csm setup" %const.COMPONENTS_CONF)
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
        Conf.load(const.INVENTORY_INDEX, Yaml(const.INVENTORY_FILE))
        Conf.load(const.COMPONENTS_INDEX, Yaml(const.COMPONENTS_CONF))

    def _config_cluster(self):
        ''' Instantiation of csm cluster with resources '''
        self._csm_resources = Conf.get(const.CSM_GLOBAL_INDEX, "HA.resources")
        self._csm_ra = {
            "csm_resource_agent": CsmResourceAgent(self._csm_resources)
        }
        self._ha_framework = PcsHAFramework(self._csm_ra)
        self._cluster = Cluster(const.INVENTORY_FILE, self._ha_framework)
        CsmApi.set_cluster(self._cluster)

    def _get_command(self):
        parser = argparse.ArgumentParser(description='CSM Setup CLI')
        subparsers = parser.add_subparsers()
        SetupCommand.add_args(subparsers)
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
        self._request = Request(self._cmd.action(), self._cmd.args())
        self.process_request(self._cmd.options(), self._process_response)
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)
        if self._response.rc() != 0:
            raise CsmError(self._response.rc(), "%s" %self._response.output())
        return self._response.output()

    def process_request(self, options, callback=None):
        Log.info('command=%s action=%s args=%s options=%s' %(self._cmd.name(),
            self._request.action(), self._request.args(), options))
        self._providers = SetupProvider(self._cluster, options)
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
    from csm.cli.commands import SetupCommand
    from csm.core.blogic import const
    from csm.core.providers.providers import Request, Response
    from csm.core.providers.setup_provider import SetupProvider
    from csm.core.blogic.csm_ha import CsmResourceAgent
    from csm.common.ha_framework import PcsHAFramework
    from csm.common.cluster import Cluster
    from csm.core.agent.api import CsmApi

    try:
        csm_setup = CsmSetup(sys.argv)
        sys.stdout.write('%s\n' %csm_setup.process())
    except CsmError as exception:
        sys.stderr.write('%s\n' %exception)
        Log.error(traceback.format_exc())
