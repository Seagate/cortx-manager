# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import os
import shutil
import subprocess

import yaml
from cortx.utils.log import Log

from csm.common.errors import CsmError
from csm.common.file_collector import LocalFileCollector, RemoteFileCollector
from csm.test.common import TestFailed

comp_rules_spec = """
s3_server:
    commands:
        - ls -l /tmp
        - uptime

    files:
        - /etc/hosts
        - /var/log/messages

motr:
    commands:
        - ls -l /tmp
        - uptime

    files:
        - /etc/hosts
"""

host_list = ['localhost']


def test1_1():
    """LocalFileCollector Test: normal case"""
    comp_rules = yaml.load(comp_rules_spec)
    Log.debug('Local File Collector Test')
    bundle_path = '/tmp/test1_bundle'
    if os.path.exists(bundle_path):
        shutil.rmtree(bundle_path)

    fc = LocalFileCollector(comp_rules, bundle_path)
    fc.collect(['s3_server', 'motr'])
    cmd = f'find {bundle_path}'
    output = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
    if len(output) == 0:
        raise TestFailed('no files collected by file collector')


def test1_2():
    """LocalFileCollector Test: Invalid Components"""
    Log.debug('Local File Collector Test')
    bundle_path = '/tmp/test1_bundle'
    try:
        LocalFileCollector(None, bundle_path)
        raise TestFailed('LocalFileCollector accepts None comp_rules')

    except CsmError:
        pass


def test1_3():
    """LocalFileCollector Test: normal case"""
    Log.debug('Local File Collector Test')
    comp_rules = yaml.load(comp_rules_spec)
    bundle_path = '/tmp/test1_bundle'
    if os.path.exists(bundle_path):
        shutil.rmtree(bundle_path)
    fc = LocalFileCollector(comp_rules, bundle_path)
    try:
        fc.collect(['dummy'])  # INVALID COMPONENT NAME
        raise TestFailed('LocalFileCollector handles dummy component')
    except CsmError:
        pass


def test2_1():
    """RemoteFileCollector Test: normal test"""
    comp_rules = yaml.load(comp_rules_spec)
    bundle_path = '/tmp/test2_bundle'
    Log.debug('Remote File Collector Test')
    if os.path.exists(bundle_path):
        shutil.rmtree(bundle_path)

    for host in host_list:
        host_bundle_path = os.path.join(bundle_path, host)
        fc = RemoteFileCollector(comp_rules, host, None, host_bundle_path)
        fc.collect(['s3_server', 'motr'])

    cmd = 'find %s' % bundle_path
    output = subprocess.check_output(cmd, stderr=subprocess.PIPE, shell=True)
    if len(output) == 0:
        raise TestFailed('no files collected by file collector')


def test2_2():
    """RemoteFileCollector Test: normal test"""
    Log.debug('Remote File Collector Test')
    bundle_path = '/tmp/test2_bundle'
    try:
        # INVALID COMPONENT RULES
        RemoteFileCollector(None, 'localhost', None, bundle_path)
        raise TestFailed('RemoteFileCollector accepts None comp_rules')

    except CsmError:
        pass


def test2_3():
    """RemoteFileCollector Test: normal test"""
    Log.debug('Remote File Collector Test')
    comp_rules = yaml.load(comp_rules_spec)
    bundle_path = '/tmp/test2_bundle'
    if os.path.exists(bundle_path):
        shutil.rmtree(bundle_path)

    for host in host_list:
        host_bundle_path = os.path.join(bundle_path, host)
        fc = RemoteFileCollector(comp_rules, host, None, host_bundle_path)

        try:
            fc.collect(['dummy'])  # INVALID COMPONENT NAME
            raise TestFailed('RemoteFileCollector handles dummy components')

        except CsmError:
            pass


test_list = [test1_1]
# test_list = [ test1_1, test1_2, test1_3, test2_1, test2_2, test2_3 ]
