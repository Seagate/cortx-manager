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
import inspect
import time
from functools import wraps
from contextlib import contextmanager
from csm.core.providers.provider_factory import ProviderFactory
from csm.core.providers.providers import Request
from csm.core.blogic import const
from csm.core.agent.api import CsmApi

class Const:
    CSM_GLOBAL_INDEX = 'CSM'
    INVENTORY_INDEX = 'INVENTORY'
    COMPONENTS_INDEX = 'COMPONENTS'
    DATABASE_INDEX = 'DATABASE'
    CSM_CONF = '/etc/csm/csm.conf'
    CSM_CONF_URL = 'yaml:///etc/csm/csm.conf'
    INVENTORY_FILE = '/etc/csm/cluster.conf'
    COMPONENTS_CONF = '/etc/csm/components.yaml'
    DATABASE_CONF = '/etc/csm/database.yaml'
    DATABASE_CONF_URL = 'yaml:///etc/csm/database.yaml'
    CSM_PATH = '/opt/seagate/cortx/csm'
    HEALTH_SCHEMA = '{}/schema/health_schema.json'.format(CSM_PATH)
    MOCK_PATH = '{}/test/test_data/'.format(CSM_PATH)
    CORTXCLI_PATH = "/opt/seagate/cortx/cli"
    CLI_SCHEMA_PATH = "{}/cli/schema".format(CORTXCLI_PATH)
    DEV = 'dev'
    STATSD_PORT = 8125
    DEV = "dev"

class TestFailed(Exception):
    def __init__(self, desc):
        desc = '[%s] %s' %(inspect.stack()[1][3], desc)
        super(TestFailed, self).__init__(desc)

class TestProvider(object):
    def __init__(self, provider_name, cluster=None):
        if cluster is None:
            CsmApi.init()
            cluster = CsmApi.get_cluster()
        self._provider = ProviderFactory.get_provider(provider_name, cluster)

    def process(self, cmd, args):
        self._response = None
        request = Request(cmd, args)
        self._provider.process_request(request, self._process_response)
        while self._response == None:
            time.sleep(const.RESPONSE_CHECK_INTERVAL)
        return self._response

    def _process_response(self, response):
        self._response = response


def get_type_name(t):
    try:
        name = t.__name__
    except AttributeError:
        name = str(t)
    return name


def async_test(coro):
    @wraps(coro)
    def wrapper(*args):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coro(args))
        return result
    return wrapper


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


def assert_equal(lhs, rhs):
    if not (lhs == rhs):
        raise TestFailed(f'"{lhs}" != "{rhs}"')


def assert_not_equal(lhs, rhs):
    if not (lhs != rhs):
        raise TestFailed(f'"{lhs}" == "{rhs}"')


@contextmanager
def assert_raises(exc_type):
    try:
        yield None
    except exc_type:
        return

    exc_name = get_type_name(exc_type)
    raise TestFailed(f'{exc_name} not raised')
