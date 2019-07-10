#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          common.py
 Description:       Common utility functions of test infrastructure

 Creation Date:     22/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import inspect
from csm.providers.provider_factory import ProviderFactory
from csm.providers.providers import Request, Response
from csm.common import const

class Const:
    INVENTORY_FILE = 'INVENTORY_FILE'
    CLUSTER = 'cluster'

class TestFailed(Exception):
    def __init__(self, desc):
        desc = '[%s] %s' %(inspect.stack()[1][3], desc)
        super(TestFailed, self).__init__(desc)

class TestProvider(object):
    def __init__(self, provider_name, cluster):
        self._provider = ProviderFactory.get_provider(provider_name, cluster)

    def start(self, cmd, args):
        self._response = None
        request = Request(cmd, args)
        self._provider.process_request(request, self.stop)
        while self._response == None: time.sleep(const.RESPONSE_CHECK_INTERVAL)

    def stop(self, response):
        self._response = response

