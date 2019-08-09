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
import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.common.errors import CsmError
from csm.core.blogic import const
from csm.common.log import Log
from csm.common.conf import Conf
from csm.common.cluster import Cluster
from csm.ras.support_bundle import SupportBundle

def init(args):
    pass

#################
# Tests
#################
def test1(args={}):
    """ Use bundle provider to create a support bundle """
    cluster = Cluster(args[Const.INVENTORY_FILE])

    components_file  = Conf.get(const.COMPONENTS_FILE, const.DEFAULT_COMPONENTS_FILE)
    components = yaml.load(open(components_file, 'r').read())

    sb = SupportBundle(cluster, components)

    bundle_name = 't1-%s' %datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Create bundle
    Log.console('Creating bundle %s' %bundle_name)
    output = sb.create(bundle_name)
    Log.console('create: output=%s' %output)

    # Confirm bundle is created
    bundle_list = sb.list()
    found = False
    bundle_root = Conf.get(const.SUPPORT_BUNDLE_ROOT, const.DEFAULT_SUPPORT_BUNDLE_ROOT)
    bundle_path = os.path.join(bundle_root, '%s.tgz' %bundle_name)
    for bundle_spec in bundle_list:
        if bundle_path not in bundle_spec.split('\t'): continue
        found = True

    if not found: raise TestFailed('bundle %s did not generate' %bundle_name)

    # Delete bundle
    Log.console('Deleting bundle %s' %bundle_name)
    output = sb.delete(bundle_name)
    Log.console('delete: output=%s' %output)

test_list = [ test1 ]
