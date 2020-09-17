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
import argparse
import traceback
import time
import pathlib


class CortxCliSetupCommand:

    """
        Provide cli to setup cortxcli. Create user for cortxcli to allow basic
        permission like log, bundle path.
    """

    def __init__(self, argv):
        """Check cortxcli setup command and initialize."""
        self._args = argv
        self._args[0] = 'cortxcli_setup'
        self._validate()
        Conf.init()
        Log.init(service_name = "cortxcli_setup", log_path = const.CORTXCLI_SETUP_LOG_DIR,
                level=const.LOG_LEVEL)

    def _validate(self):
        """Validate setup command."""
        if len(self._args) < 2:
            raise Exception('Usage: cortxcli_setup -h')

    def _get_command(self):
        """Parse cortxcli setup command."""
        parser = argparse.ArgumentParser(description='CORTX CLI Setup', usage='')
        subparsers = parser.add_subparsers()
        # hardcoded permissions
        cortxcli_setup_permissions_dict = {'update': True}
        cmd_obj = CommandParser(Json(const.CORTXCLI_SETUP_FILE).load(), cortxcli_setup_permissions_dict)
        cmd_obj.handle_main_parse(subparsers)
        namespace = parser.parse_args(self._args)
        sys_module = sys.modules[__name__]
        for attr in ['command', 'action', 'args']:
            setattr(sys_module, attr, getattr(namespace, attr))
            delattr(namespace, attr)
        return command(action, vars(namespace), args) # pylint: disable=undefined-variable

    def process(self):
        """Parse args for cortxcli_setup and execute cmd to print output."""
        self._cmd = self._get_command()
        self._response = None
        self._request = Request(self._cmd._name, self._cmd.args, self._cmd.options)
        self.process_request(self._process_response)
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)
        if self._response.rc() != 0:
            raise CsmSetupError("%s" %self._response.output())
        return self._response.output()

    def process_request(self, callback=None):
        self._providers = SetupProvider()
        return self._providers.process_request(self._request, callback)

    def _process_response(self, response):
        self._response = response

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    from csm.common.conf import Conf
    from csm.common.payload import *
    from csm.common.payload import Json
    from csm.common.errors import CsmSetupError
    from csm.cli.command import CommandParser
    from csm.core.blogic import const
    from csm.core.providers.providers import Request
    from csm.core.providers.cortxcli_setup_provider import SetupProvider
    from eos.utils.log import Log
    try:
        cortxcli_setup = CortxCliSetupCommand(sys.argv)
        sys.stdout.write('%s\n' % cortxcli_setup.process())
        sys.exit(0)
    except Exception:
        sys.stderr.write('cortxcli_setup command failed: %s\n' %traceback.format_exc())
        sys.exit(1)
