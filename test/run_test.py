#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          run_test.py
 Description:       Initiates execution of all the tests

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
import errno
import re
import yaml
import argparse

from csm.common.log import Log
from csm.core.blogic import const
from csm.common.errors import CsmError
from csm.common.payload import *
from csm.common.conf import Conf
from csm.test.common import TestFailed, Const
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.common.ha_framework import PcsHAFramework
from csm.common.cluster import Cluster
from csm.core.agent.api import CsmApi

def tmain(argp, argv):
    # Import required TEST modules
    ts_path = os.path.dirname(argv)
    sys.path.append(os.path.join(ts_path, '..', '..'))

    # Perform validation of setup before tests are run
    try:
        csm_conf = const.CSM_CONF
        if not os.path.exists(csm_conf):
            raise TestFailed('%s not present. Refer to samples directory' %csm_conf)

        Log.init('csm', '/tmp')
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(csm_conf))

        inventory_file = const.INVENTORY_FILE
        if not os.path.exists(inventory_file):
            raise TestFailed('Missing config file %s' %inventory_file)

    except TestFailed as e:
        print('Test Pre-condition failed. %s' %e)
        sys.exit(errno.ENOENT)

    # Initialization
    try:
        test_args_file = argp.f if argp.f is not None else os.path.join(ts_path, 'args.yaml')
        args = yaml.safe_load(open(test_args_file, 'r').read())
        if args is None: args = {}

        # Read inventory data and collection rules from file
        args[Const.INVENTORY_FILE] = inventory_file
    except TestFailed as e:
        print('Test Initialization failed. %s' %e)
        sys.exit(errno.ENOENT)

    # Cluster Instantiation
    try:
        csm_resources = Conf.get(const.CSM_GLOBAL_INDEX, "HA.resources")
        csm_ra = {
            "csm_resource_agent": CsmResourceAgent(csm_resources)
        }
        ha_framework = PcsHAFramework(csm_ra)
        cluster = Cluster(const.INVENTORY_FILE, ha_framework)
        CsmApi.set_cluster(cluster)
    except TestFailed as e:
        print('Test Initialization of cluster failed. %s' %e)
        sys.exit(errno.ENOENT)

    # Prepare to run the test, all or subset per command line args
    ts_list = []
    if argp.t is not None:
        if not os.path.exists(argp.t):
            raise TestFailed('Missing file %s' %argp.t)
        with open(argp.t) as f:
            content = f.readlines()
            ts_list = [x.strip() for x in content]
    else:
        file_path = os.path.dirname(os.path.realpath(__file__))
        for root, directories, filenames in os.walk(os.getcwd()):
            for filename in filenames:
                if re.match(r'test_.*\.py$', filename):
                    file = os.path.join(root, filename).rsplit('.', 1)[0]\
                        .replace(file_path + "/", "").replace("/", ".")
                    ts_list.append(file)

    ts_count = test_count = pass_count = fail_count = 0
    ts_start_time = time.time()
    for ts in ts_list:
        print('\n####### Test Suite: %s ######' %ts)
        ts_count += 1
        try:
            ts_module = __import__('csm.test.%s' %ts, fromlist=[ts])
            # Initialization
            init = getattr(ts_module, 'init')
            init(args)
        except Exception as e:
            print('FAILED: Error: %s #@#@#@' %e)
            fail_count += 1
            Log.exception(e)
            continue

        # Actual test execution
        for test in ts_module.test_list:
            test_count += 1
            try:
                start_time = time.time()
                test(args)
                duration = time.time() - start_time
                print('%s:%s: PASSED (Time: %ds)' %(ts, test.__name__, duration))
                pass_count += 1

            except (CsmError, TestFailed, Exception) as e:
                Log.exception(e)
                print('%s:%s: FAILED #@#@#@' %(ts, test.__name__))
                print('    %s\n' %e)
                fail_count += 1

    duration = time.time() - ts_start_time
    print('\n***************************************')
    print('TestSuite:%d Tests:%d Passed:%d Failed:%d TimeTaken:%ds' \
        %(ts_count, test_count, pass_count, fail_count, duration))
    print('***************************************')

if __name__ == '__main__':
    try:
        argParser = argparse.ArgumentParser(
            usage = "%(prog)s [-h] [-t] [-f]",
            formatter_class = argparse.RawDescriptionHelpFormatter)
        argParser.add_argument("-t",
                help="Enter path of testlist file")
        argParser.add_argument("-f",
                help="Enter path of args.yaml")
        args = argParser.parse_args()

        args = argParser.parse_args()
        tmain(args, sys.argv[0])
    except Exception as e:
        print(e, traceback.format_exc())
        Log.exception(e)
