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

import sys, os, time
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from cortx.utils.log import Log
from csm.core.agent.api import CsmApi
from csm.core.providers.providers import Request, Response
from csm.core.providers.setup_provider import SetupProvider

class TestSetupProvider:
    def __init__(self):
        options = {'f':False}
        self._cluster = CsmApi.get_cluster()
        self._provider = SetupProvider(self._cluster, options)

    def process(self, cmd, args):
        self._response = None
        request = Request(cmd, args)
        self._provider.process_request(request, self._process_response)
        while self._response == None:
            time.sleep(const.RESPONSE_CHECK_INTERVAL)
        return self._response

    def _process_response(self, response):
        self._response = response

def init(args):
    pass

#################
# Tests
#################
def test1(args):
    """ Use init provider to initalize csm """

    tp = TestSetupProvider()
    arg_list = []

    # Init Component
    Log.console('Initalizing CSM Component ...')
    response = tp.process('init', arg_list)
    if response.rc() != 0: raise TestFailed('%s' %response.output())
    Log.console('Init CSM: response=%s' %response)

test_list = [ test1 ]
