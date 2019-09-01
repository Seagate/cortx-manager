#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_init_provider.py
 Description:       Test init provider for csm.

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
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from csm.common.log import Log
from csm.core.agent.api import CsmApi
from csm.core.providers.providers import Request, Response
from csm.core.providers.setup_provider import SetupProvider

class TestSetupProvider:
    def __init__(self):
        self._cluster = CsmApi.get_cluster()
        self._provider = SetupProvider(self._cluster)

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
