#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_csm_ha_service.py
 Description:       Test csm_agent and csm_web status.

 Creation Date:     07/08/2019
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


test_list = [ test_csm_agent, test_csm_web ]
