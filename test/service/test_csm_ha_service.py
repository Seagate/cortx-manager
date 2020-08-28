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
import time
import requests
import provisioner
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.conf import Conf
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from eos.utils.log import Log

def init(args):
    pass

def get_mgmt_vip():
    """
    Initialize csm test
    self.mgmt_vip: {'srvnode-1': {'network/mgmt_vip': '10.230.255.16'},
                    'srvnode-2': {'network/mgmt_vip': '10.230.255.16'}}
    """
    mgmt_vips = provisioner.get_params('network/mgmt_vip')
    Log.console(f"Management network ip: {mgmt_vips}")
    return mgmt_vips

def process_request(url):
    return requests.get(url, verify=False)

#################
# Tests         #
#################
def test_csm_agent(args):
    """
    Check status for csm agent service
    """
    try:
        Log.console('\n\n********************* Testing csm_agent ********************')
        time.sleep(5)
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.ssl_check")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.port")
        url = "http://" if not ssl_check else "https://"
        mgmt_vips = get_mgmt_vip()
        for node in mgmt_vips.keys():
            csm_url = url + mgmt_vips[node]['network/mgmt_vip'] + ":" + str(port)
            resp = process_request(csm_url)
            Log.console(f"Request: {csm_url}, Responce: {resp}")
            if resp.status_code != 401:
                raise
    except Exception as e:
        raise TestFailed("csm_agent service is not running. Error: %s" %traceback.format_exc())

def test_csm_web(args):
    """
    Check status for csm web service
    """
    try:
        Log.console('\n\n********************* Testing csm_web *****************************')
        time.sleep(5)
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.ssl_check")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.port")
        url = "http://" if not ssl_check else "https://"
        mgmt_vips = get_mgmt_vip()
        for node in mgmt_vips.keys():
            csm_url = url + mgmt_vips[node]['network/mgmt_vip'] + ":" + str(port)
            resp = process_request(csm_url)
            Log.console(f"Request: {csm_url}, Responce: {resp}")
            if resp.status_code != 200:
                raise
    except Exception as e:
        raise TestFailed("csm_web service is not running. Error: %s" %traceback.format_exc())


test_list = [ test_csm_agent ]
