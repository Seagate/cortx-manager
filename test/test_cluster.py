#!/usr/bin/python

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
import yaml
import getpass

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.cluster import Cluster, Node
from csm.common.errors import CsmError
from csm.common.log import Log
from csm.common import const
from csm.test.common import TestFailed

cluster_info  = {
    'SSU': {
        'sw_components': [ 'os', 'mero', 'halon' ],
        'nodes': [ 'ssu1-h1', 'ssu2-h1', 'ssu3-h1', 'ssu4-h1', 'ssu5-h1', 'ssu6-h1', 'ssu7-h1' ]
    },
    'S3_SERVER': {
        'sw_components': [ 'os', 'mero', 'halon' ],
        'nodes': [ 'qb01n1-h1', 'qb01n2-h1', 'qb01n3-h1', 'qb01n4-h1' ]
    },
    'CMU': {
        'sw_components': [ 'os', 's3_cli' ],
        'nodes': [ 'cmu-h1' ]
    },
    'S3_LOAD_BALANCER': {
        'sw_components': [ ],
        'nodes': [ 'qb01n1-h1', 'qb01n2-h1' ]
    }
}

cluster_hosts = [ 'ssu1-h1', 'ssu2-h1', 'ssu3-h1', 'ssu4-h1', 'ssu5-h1', 'qb01n3-h1',
                  'ssu6-h1', 'ssu7-h1', 'cmu-h1', 'qb01n1-h1', 'qb01n2-h1', 'qb01n4-h1']
cluster_ssu_hosts = [ 'ssu1-h1', 'ssu2-h1', 'ssu3-h1', 'ssu4-h1', 'ssu5-h1', 'ssu6-h1', 'ssu7-h1' ]
cluster_ssu_components = [ 'os', 'mero', 'halon' ]
inventory_file = '/tmp/cluster.yaml'

def init(args):
    with open(inventory_file, 'w') as f:
        for node_type in cluster_info.keys():
            f.write('%s:\n' %node_type)
            f.write('    sw_components: %s\n' %cluster_info[node_type]['sw_components'])
            f.write('    nodes: %s\n' %cluster_info[node_type]['nodes'])

def test1(args={}):
    """ Normal cases """
    cluster = Cluster(inventory_file)
    host_list = cluster.host_list()
    if len([x for x in host_list if x not in cluster_hosts]) != 0:
        raise TestFailed('host list not obtained properly')

    any_node = cluster.node_list()[0]

    if getpass.getuser() != any_node.user():
        raise TestFailed('Node user is not set for node %s' %any_node)

    ssu_components = cluster.sw_components(const.TYPE_SSU)
    if len([x for x in ssu_components if x not in cluster_ssu_components]) != 0:
        raise TestFailed('SSU components mismatch. Expected: %s Actual: %s' \
                %(cluster_ssu_components, ssu_components))

    ssu_hosts = cluster.host_list(const.TYPE_SSU)
    if len([x for x in ssu_hosts if x not in cluster_ssu_hosts]) != 0:
        raise TestFailed('SSU hosts mismatch. Expected: %s Actual: %s' \
                %(cluster_ssu_hosts, ssu_hosts))

def test2(args={}):
    """ Negative Test """
    try:
        cluster = Cluster('/tmp/non-existing-file')
        raise TestFailed('No exception raised for non existing cluster config file')
    except: pass

test_list = [ test1, test2 ]
