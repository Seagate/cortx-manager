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

import sys, os
import time
import requests
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from cortx.utils.conf_store.conf_store import Conf
from csm.test.common import TestFailed
from csm.core.blogic import const
from cortx.utils.log import Log

def init(args):
    pass

def process_request(url):
    return requests.get(url, verify=False)

#################
# Tests
#################
def test1(args):
    """
    Check status for csm agent service
    """
    try:
        Log.console('Testing csm_agent service ...')
        time.sleep(5)
        ssl_check = (Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE>CSM_AGENT>ssl_check") == 'true')
        host = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE>CSM_AGENT>host")
        port = int(Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE>CSM_AGENT>port"))
        url = "http://" if not ssl_check else "https://"
        url = url + host + ":" + str(port)
        process_request(url)
    except requests.exceptions.RequestException:
        raise TestFailed("csm_agent service is not running. Error: %s" %traceback.format_exc())

def test2(args):
    """
    Check status for csm web service
    """
    try:
        Log.console('Testing csm_web service ...')
        time.sleep(5)
        ssl_check = (Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE>CSM_WEB>ssl_check") == 'true')
        host = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE>CSM_WEB>host")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE>CSM_WEB>port")
        url = "http://" if not ssl_check else "https://"
        url = url + host + ":" + str(port)
        process_request(url)
    except requests.exceptions.RequestException:
        raise TestFailed("csm_web service is not running. Error: %s" %traceback.format_exc())

test_list = [ test1 ]
