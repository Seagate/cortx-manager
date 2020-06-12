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

import sys
import os
import time
import traceback
import errno
import re
import yaml
import argparse
import pathlib

def is_file_exists(fi):
    if not os.path.exists(fi):
        raise TestFailed('%s file is not present...' %fi)
    return fi

def tmain(argp, argv):
    # Import required TEST modules
    ts_path = os.path.dirname(argv)
    sys.path.append(os.path.join(ts_path, '..', '..'))

    # Perform validation and Initialization
    try:
        Conf.init()
        Conf.load(Const.CSM_GLOBAL_INDEX, Yaml(is_file_exists(Const.CSM_CONF)))
        Conf.load(Const.INVENTORY_INDEX, Yaml(is_file_exists(Const.INVENTORY_FILE)))
        Conf.load(Const.COMPONENTS_INDEX, Yaml(is_file_exists(Const.COMPONENTS_CONF)))
        Conf.load(Const.DATABASE_INDEX, Yaml(is_file_exists(Const.DATABASE_CONF)))
        if ( Conf.get(Const.CSM_GLOBAL_INDEX, "DEPLOYMENT.mode") != Const.DEV ):
            Conf.decrypt_conf()
        if argp.l:
            Log.init("csm_test", log_path=argp.l)
        else:
            Log.init("csm_test",
             log_path=Conf.get(Const.CSM_GLOBAL_INDEX, "Log.log_path"),
             level=Conf.get(Const.CSM_GLOBAL_INDEX, "Log.log_level"))
        test_args_file = argp.f if argp.f is not None else os.path.join(ts_path, 'args.yaml')
        args = yaml.safe_load(open(test_args_file, 'r').read())
        if args is None: args = {}
    except TestFailed as e:
        print('Test Pre-condition failed. %s' %e)
        sys.exit(errno.ENOENT)

    # Prepare to run the test, all or subset per command line args
    ts_list = []
    if argp.t is not None:
        if not os.path.exists(argp.t):
            raise TestFailed('Missing file %s' %argp.t)
        with open(argp.t) as f:
            content = f.readlines()
            for x in content:
                if not x.startswith('#'):
                    ts_list.append(x.strip())
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
            import traceback
            traceback.print_exc()
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
    if argp.o is not None:
        with open(argp.o, "w") as f:
            status = "Failed" if fail_count != 0 else "Passed"
            f.write(status)

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..', '..'))
    from eos.utils.log import Log
    from csm.common.errors import CsmError
    from csm.common.payload import *
    from csm.common.conf import Conf
    from csm.test.common import TestFailed, Const

    try:
        argParser = argparse.ArgumentParser(
            usage = "%(prog)s [-h] [-t] [-f] [-l] [-o]",
            formatter_class = argparse.RawDescriptionHelpFormatter)
        argParser.add_argument("-t",
                help="Enter path of testlist file")
        argParser.add_argument("-f",
                help="Enter path of args.yaml")
        argParser.add_argument("-l",
                help="Enter path for log file")
        argParser.add_argument("-o",
                help="Print final result in file return fail if any one of test failed.")
        args = argParser.parse_args()

        args = argParser.parse_args()
        tmain(args, sys.argv[0])
    except Exception as e:
        print(e, traceback.format_exc())
        Log.exception(e)
