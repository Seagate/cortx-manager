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

import sys, os
import subprocess
import shutil
import yaml
import getpass

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.cluster import Cluster, Node
from csm.common.errors import CsmError
from eos.utils.log import Log
from csm.core.blogic import const
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
