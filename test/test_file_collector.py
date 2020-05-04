#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          run_file_collector.py
 _description:      Test File Collection infrastructure

 Creation Date:     30/06/2018
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

import sys, os
import subprocess
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.file_collector import RemoteFileCollector, LocalFileCollector
from csm.common.errors import CsmError
from eos.utils.log import Log
from csm.test.common import TestFailed
import yaml

comp_rules_spec = '''
s3_server:
    commands:
        - ls -l /tmp
        - uptime

    files:
        - /etc/hosts
        - /var/log/messages

mero:
    commands:
        - ls -l /tmp
        - uptime

    files:
        - /etc/hosts
'''

host_list = ['localhost']

def init(args):
    pass

def test1_1(args={}):
    """ LocalFileCollector Test: normal case """
    comp_rules = yaml.load(comp_rules_spec)
    Log.debug('Local File Collector Test')
    bundle_path = '/tmp/test1_bundle'
    if os.path.exists(bundle_path): shutil.rmtree(bundle_path)

    fc = LocalFileCollector(comp_rules, bundle_path)
    fc.collect(['s3_server', 'mero'])
    cmd = 'find %s' %bundle_path
    output = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
    if len(output) == 0: raise TestFailed('no files collected by file collector')

def test1_2(args={}):
    """ LocalFileCollector Test: Invalid Components """
    Log.debug('Local File Collector Test')
    bundle_path = '/tmp/test1_bundle'
    try:
        fc = LocalFileCollector(None, bundle_path)
        raise TestFailed('LocalFileCollector accepts None comp_rules')

    except CsmError as e:
        pass

def test1_3(args={}):
    """ LocalFileCollector Test: normal case """
    Log.debug('Local File Collector Test')
    comp_rules = yaml.load(comp_rules_spec)
    bundle_path = '/tmp/test1_bundle'
    if os.path.exists(bundle_path): shutil.rmtree(bundle_path)
    fc = LocalFileCollector(comp_rules, bundle_path)
    try:
        fc.collect(['dummy']) # INVALID COMPONENT NAME
        raise TestFailed('LocalFileCollector handles dummy component')
    except CsmError as e:
        pass

def test2_1(args={}):
    """ RemoteFileCollector Test: normal test """
    comp_rules = yaml.load(comp_rules_spec)
    bundle_path = '/tmp/test2_bundle'
    Log.debug('Remote File Collector Test')
    if os.path.exists(bundle_path): shutil.rmtree(bundle_path)

    for host in host_list:
        host_bundle_path = os.path.join(bundle_path, host)
        fc = RemoteFileCollector(comp_rules, host, None, host_bundle_path)
        fc.collect(['s3_server', 'mero'])

    cmd = 'find %s' %bundle_path
    output = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
    if len(output) == 0: raise TestFailed('no files collected by file collector')

def test2_2(args={}):
    """ RemoteFileCollector Test: normal test """
    Log.debug('Remote File Collector Test')
    bundle_path = '/tmp/test2_bundle'
    try:
        # INVALID COMPONENT RULES
        fc = RemoteFileCollector(None, 'localhost', None, bundle_path)
        raise TestFailed('RemoteFileCollector accepts None comp_rules')

    except CsmError as e:
        pass

def test2_3(args={}):
    """ RemoteFileCollector Test: normal test """
    Log.debug('Remote File Collector Test')
    comp_rules = yaml.load(comp_rules_spec)
    bundle_path = '/tmp/test2_bundle'
    if os.path.exists(bundle_path): shutil.rmtree(bundle_path)

    for host in host_list:
        host_bundle_path = os.path.join(bundle_path, host)
        fc = RemoteFileCollector(comp_rules, host, None, host_bundle_path)

        try:
            fc.collect(['dummy']) # INVALID COMPONENT NAME
            raise TestFailed('RemoteFileCollector handles dummy components')

        except CsmError as e:
            pass

test_list = [ test1_1 ]
#test_list = [ test1_1, test1_2, test1_3, test2_1, test2_2, test2_3 ]
