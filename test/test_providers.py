#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_support_bundle.py
 Description:       Test support bundle functionality i.e. create, delete and
                    list support bundles.

 Creation Date:     22/06/2018
 Author:            Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os, time
import traceback
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.cluster import Cluster, Node
from csm.test.common import TestFailed, TestProvider, Const
from csm.common.errors import CsmError
from csm.core.blogic import const
from csm.common.conf import Conf
from csm.common.log import Log

class TestBundleProvider(TestProvider):
    def __init__(self, cluster):
        super(TestBundleProvider, self).__init__(const.SUPPORT_BUNDLE, cluster)

    def create(self, bundle_name):
        return self.process('create', [bundle_name])

    def delete(self, bundle_name):
        return self.process('delete', [bundle_name])

    def list(self):
        return self.process('list', [])

def init(args):
    args[Const.CLUSTER] = Cluster(args[Const.INVENTORY_FILE])

#################
# Tests
#################
def test1(args):
    """ Use bundle provider to create a support bundle """
    tp = TestBundleProvider(args[Const.CLUSTER])
    bundle_name = 'test1-%s' %datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Create bundle
    Log.console('Creating bundle %s' %bundle_name)
    response = tp.create(bundle_name)
    if response.rc() != 0: raise TestFailed('%s' %response)
    Log.console('create: response=%s' %response)

    # Confirm bundle is created
    response = tp.list()
    bundle_list = response.output().split('\n')
    bundle_root = Conf.get(const.CSM_GLOBAL_INDEX,
        const.SUPPORT_BUNDLE_ROOT, const.DEFAULT_SUPPORT_BUNDLE_ROOT)
    bundle_path = os.path.join(bundle_root, '%s.tgz' %bundle_name)
    found = False
    for bundle_spec in bundle_list:
        if bundle_path not in bundle_spec.split('\t'): continue
        found = True

    if not found: raise TestFailed('bundle %s did not generate' %bundle_name)

    # Delete bundle
    Log.console('Deleting bundle %s' %bundle_name)
    response = tp.delete(bundle_name)
    if response.rc() != 0: raise TestFailed('%s' %response)
    Log.console('delete: response=%s' %response)

test_list = [ test1 ]
