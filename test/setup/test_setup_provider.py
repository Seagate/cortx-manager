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

import time

from cortx.utils.log import Log

from csm.core.agent.api import CsmApi
from csm.core.blogic import const
from csm.core.providers.providers import Request
from csm.core.providers.setup_provider import SetupProvider
from csm.test.common import TestFailed


class TestSetupProvider:
    def __init__(self):
        options = {'f': False}
        self._cluster = CsmApi.get_cluster()
        self._provider = SetupProvider(self._cluster, options)
        self._response = None

    def process(self, cmd, args):
        self._response = None
        request = Request(cmd, args)
        self._provider.process_request(request, self._process_response)
        while self._response is None:
            time.sleep(const.RESPONSE_CHECK_INTERVAL)
        return self._response

    def _process_response(self, response):
        self._response = response


def test1():
    """Use init provider to initialize csm"""
    tp = TestSetupProvider()
    arg_list = []

    # Init Component
    Log.console('Initalizing CSM Component ...')
    response = tp.process('init', arg_list)
    if response.rc() != 0:  # pylint: disable=no-member
        raise TestFailed(str(response.output()))  # pylint: disable=no-member
    Log.console('Init CSM: response=%s' % response)


test_list = [test1]
