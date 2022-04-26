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

import asyncio
import sys
import os
import argparse
import traceback
import pathlib

class CsmSetupCommand:
    """
        Provide cli to setup csm. Create user for csm to allow basic
        permission like log, bundle path.
    """

    def __init__(self, argv):
        """Check csm setup command and initialize."""
        self._args = argv
        self._args[0] = 'csm_setup'
        self._validate()
        self._loop = asyncio.get_event_loop()
        Conf.init()
        Log.init(service_name = "csm_setup", log_path = const.CSM_SETUP_LOG_DIR,
                level=const.LOG_LEVEL)

    def _validate(self):
        """Validate setup command."""
        if len(self._args) < 2:
            raise Exception('Usage: csm_setup -h')

    def _get_command(self):
        """Parse csm setup command."""
        parser = argparse.ArgumentParser(description='CSM Setup CLI', usage='')
        subparsers = parser.add_subparsers()
        # hardcoded permissions
        csm_setup_permissions_dict = {'update': True}
        cmd_obj = CommandParser(Json(const.CSM_SETUP_FILE).load(), csm_setup_permissions_dict)
        cmd_obj._handle_main_parse(subparsers)
        namespace = parser.parse_args(self._args)
        sys_module = sys.modules[__name__]
        for attr in ['command', 'action', 'args']:
            setattr(sys_module, attr, getattr(namespace, attr))
            delattr(namespace, attr)
        return command(action, vars(namespace), args)

    def process(self):
        """Parse args for csm_setup and execute cmd to print output."""
        self._cmd = self._get_command()
        obj = CliClient()
        response = self._loop.run_until_complete(obj.call(self._cmd))
        if response:
            self._cmd.process_response(out=sys.stdout, err=sys.stderr,
                                     response=response)

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..'))
    from cortx.utils.conf_store.conf_store import Conf
    from csm.common.payload import *
    from cortx.utils.cli_framework.parser import CommandParser
    from csm.core.blogic import const
    from cortx.utils.log import Log
    from cortx.utils.cli_framework.client import CliClient
    from csm.conf.post_install import PostInstall
    from csm.conf.prepare import Prepare
    from csm.conf.configure import Configure
    from csm.conf.init import Init
    from csm.conf.reset import Reset
    from csm.conf.test import Test
    from csm.conf.upgrade import Upgrade
    from csm.conf.pre_upgrade import PreUpgrade
    from csm.conf.post_upgrade import PostUpgrade
    from csm.conf.cleanup import Cleanup

    try:
        csm_setup = CsmSetupCommand(sys.argv)
        csm_setup.process()
        sys.exit(0)
    except Exception:
        sys.stderr.write('csm_setup command failed: %s\n' %traceback.format_exc())
        sys.exit(1)
