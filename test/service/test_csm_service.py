#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_systemd_service.py
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

import sys, os
import time
import asyncio
import requests
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.conf import Conf
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from csm.common.log import Log
from csm.common.errors import CsmError

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
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.ssl_check")
        host = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.host")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_AGENT.port")
        url = "http://" if not ssl_check else "https://"
        url = url + host + ":" + str(port)
        resp = process_request(url)
        if resp.status_code != 401:
            raise
    except Exception as e:
        raise TestFailed("csm_agent service is not running. Error: %s" %traceback.format_exc())

def test2(args):
    """
    Check status for csm web service
    """
    try:
        Log.console('Testing csm_web service ...')
        ssl_check = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.ssl_check")
        host = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.host")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "CSM_SERVICE.CSM_WEB.port")
        url = "http://" if not ssl_check else "https://"
        url = url + host + ":" + str(port)
        resp = process_request(url)
        if resp.status_code != 200:
            raise
    except Exception as e:
        raise TestFailed("csm_web service is not running. Error: %s" %traceback.format_exc())

test_list = [ test1, test2 ]
