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
from csm.common.cluster import Cluster
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from csm.common.log import Log
from csm.core.api.api import CsmApi

class TestSetupProvider(TestProvider):
    def __init__(self):
        super(TestSetupProvider, self).__init__(const.CSM_SETUP_CMD)

    def setup_csm(self, action, args):
        return self.process(action, args)

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
    response = tp.setup_csm('init', arg_list)

    if response.rc() != 0: raise TestFailed('%s' %response.output())
    Log.console('Init CSM: response=%s' %response)

test_list = [ test1 ]
