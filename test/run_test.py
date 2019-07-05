#!/usr/bin/python

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
from csm.common import const
from csm.common.errors import CsmError
from csm.common.payload import *
from csm.common.conf import Conf
from csm.test.common import TestFailed, Const
from csm.common.cluster import Cluster

def tmain(argp, argv):
    # Import required TEST modules
    ts_path = os.path.dirname(argv)
    sys.path.append(os.path.join(ts_path, '..', '..'))

    # Perform validation of setup before tests are run
    try:
        if not os.path.exists('/etc/csm/csm.conf'):
            raise TestFailed('/etc/csm/csm.conf not present. Refer to samples directory')

        Log.init('csm', '/tmp')
        Conf.init(Toml('/etc/csm/csm.conf'))

        inventory_file = Conf.get(const.INVENTORY_FILE, const.DEFAULT_INVENTORY_FILE)
        if not os.path.exists(inventory_file):
            raise TestFailed('Missing config file %s' %inventory_file)

    except TestFailed as e:
        print('Test Pre-condition failed. %s' %e)
        sys.exit(errno.ENOENT)

    # Initialization
    try:
        test_args_file = os.path.join(ts_path, 'args.yaml')
        args = yaml.safe_load(open(test_args_file, 'r').read())
        if args is None: args = {}

        # Read inventory data and collection rules from file
        args[Const.INVENTORY_FILE] = inventory_file

    except TestFailed as e:
        print('Test Initialization failed. %s' %e)
        sys.exit(errno.ENOENT)

    # Prepare to run the test, all or subset per command line args
    ts_list = []
    if argp.f is not None:
        if not os.path.exists(argp.f):
            raise TestFailed('Missing file %s' %argp.f)
        with open(argp.f) as f:
            content = f.readlines()
            ts_list = [x.strip() for x in content]
    else:
        path = argp.r if argp.d is None else argp.d
        for root, directories, filenames in os.walk(path):
            for filename in filenames:
                if re.match(r'.*\.lst$', filename) and argp.d is not None:
                    with open(os.path.join(root, filename)) as f:
                        content = f.readlines()
                        ts_list = ts_list + [x.strip() for x in content]
                elif re.match(r'test_.*\.py$', filename) and argp.d is None:
                    file = (os.path.join(root, filename).rsplit('.', 1)[0])\
                            .replace(argp.r, "").replace("/", ".")
                    ts_list.append(file[1::] if file.startswith('.') else file)

    ts_count = test_count = pass_count = fail_count = 0
    ts_start_time = time.time()
    for ts in ts_list:
        print('\n####### Test Suite: %s ######' %ts)
        ts_count += 1
        ts_module = __import__('csm.test.%s' %ts, fromlist=[ts])

        # Initialization
        try:
            init = getattr(ts_module, 'init')
            init(args)
        except Exception as e:
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
            usage = "%(prog)s [-h] [-d] [-f]",
            formatter_class = argparse.RawDescriptionHelpFormatter)
        argParser.add_argument("-d",
                help="Enter dir path having testlist files")
        argParser.add_argument("-f",
                help="Enter path of testlist file")
        argParser.add_argument("-r",
                help="Search recursively for all test_*.py on given path",
                default=Const.TESTDIR)
        args = argParser.parse_args()

        args = argParser.parse_args()
        tmain(args, sys.argv[0])
    except Exception as e:
        print(e, traceback.format_exc())
        Log.exception(e)
