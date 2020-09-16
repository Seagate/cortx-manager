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
import traceback

import requests
from cortx.utils.log import Log

from csm.common.conf import Conf
from csm.core.blogic import const
from csm.test.common import TestFailed


def process_request(url):
    return requests.get(url, verify=False)

#################
# Tests
#################


def test1():
    """Check status for csm agent service"""
    Log.console('Testing csm_agent service ...')
    time.sleep(5)
    ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.ssl_check")
    host = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.host")
    port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.port")
    url = f'{"http://" if not ssl_check else "https://"}{host}:{port}'
    resp = process_request(url)
    if resp.status_code != 401:
        raise TestFailed(f"csm_agent service is not running. Error: {traceback.format_exc()}")


def test2():
    """Check status for csm web service"""
    Log.console('Testing csm_web service ...')
    time.sleep(5)
    ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.ssl_check")
    host = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.host")
    port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.port")
    url = f'{"http://" if not ssl_check else "https://"}{host}:{port}'
    resp = process_request(url)
    if resp.status_code != 200:
        raise TestFailed(f"csm_web service is not running. Error: {traceback.format_exc()}")


test_list = [test1]
