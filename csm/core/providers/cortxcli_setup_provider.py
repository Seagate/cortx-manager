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

import os
import sys
import errno
from csm.conf.cortx_cli_setup import CortxCliSetup
from csm.core.blogic import const
from csm.core.providers.providers import Provider, Request, Response

class SetupProvider(Provider):
    """
    Provider implementation for csm initialization
    """
    def __init__(self):
        super(SetupProvider, self).__init__(const.CORTXCLI_SETUP_CMD)
        self._cortxcli_setup = CortxCliSetup()
        self.arg_list = {}

    def _validate_request(self, request):
        """
        Validate setup command request
        """
        self._action = request.options["sub_command_name"]

    def _process_request(self, request):
        try:
            getattr(self._cortxcli_setup, "%s" %(self._action))(request.options)
            return Response(0, "CSM %s : PASS" %self._action)
        except Exception as e:
            return Response(errno.EINVAL, "CSM %s : Fail %s" %(self._action,e))
