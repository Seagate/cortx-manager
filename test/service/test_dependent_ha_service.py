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
import time
import json
import requests
import random
# Package statsd removed from csm
# Todo: Code clean up will be covered in future sprint
from statsd import StatsClient
import provisioner
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from csm.common.comm import SSHChannel

def init(args):
    pass

def get_nodes_id():
    """
    Output: {'srvnode-1': '19cda47f-34b2-47ac-9668-c8e2e646c00f',
            'srvnode-2': '490b21de-61e9-4e63-8c9c-a45cca9b1afb'}
    """
    nodes_id = provisioner.get_node_id()
    Log.console(f"Node ID list: {nodes_id}")
    return nodes_id

def process_request(url):
    return requests.get(url)

def ssh_execute(nodes, cmds):
    """
    Execute command and return list
    """
    try:
        result = {}
        ssh_key = os.path.expanduser(os.path.join("~", const.SSH_DIR, const.SSH_KEY))
        for node in nodes:
            result[node] = 0
            channel = SSHChannel(node, 'root', allow_agent=True, key_filename=ssh_key)
            channel.connect()
            for cmd in cmds:
                rc, output = channel.execute(cmd)
                Log.console(f"node:{node} cmd:{cmd}, rc:{rc}, output:{output}")
                if rc != 0:
                    result[node] = rc
                    channel.disconnect()
                    break
            channel.disconnect()
        return result
    except Exception as e:
        raise e

#################
# Tests
#################
def test_statsd(args):
    """
    Check status for statsd service
    """
    try:
        Log.console("\n\n************* Testing Statsd *******************")
        for node in get_nodes_id().keys():
            c = StatsClient(node, Const.STATSD_PORT)
            Log.console(f"node: {node}, statsd_client: {c}")
    except Exception as e:
        raise TestFailed("statsd service is not running. Error: %s" %traceback.format_exc())

def test_kibana(args):
    """
    Check status for Kibana service
    """
    try:
        time.sleep(5)
        Log.console("\n\n************* Testing Kibana service *********************")
        host = Conf.get(const.CSM_GLOBAL_INDEX, "STATS>PROVIDER>host")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "STATS>PROVIDER>port")
        url = "http://" + host + ":" + str(port)
        cmds = ["systemctl is-active kibana.service", "curl "+ url]
        results = ssh_execute(list(get_nodes_id().keys()), cmds)
        if 0 in results.values():
            for result in results.keys():
                if results[result] != 0:
                    return
        raise TestFailed("%s instace of kibana running on system" %results.keys())
    except Exception as e:
        raise TestFailed("Kibana is not working. Exception %s ..." %e)

def test_elasticsearch(args):
    """
    Check if elasticsearch is running on system
    """
    try:
        time.sleep(5)
        Log.console("\n\n*************** Testing Elasticsearch service *********************")
        db = Conf.get(const.DATABASE_INDEX, "databases")["es_db"]["config"]
        url = "http://" + db["host"] + ":" + str(db["port"])
        cmds = ["systemctl is-active elasticsearch.service", "curl "+ url]
        results = ssh_execute(list(get_nodes_id().keys()), cmds)
        for result in results.values():
            if result != 0:
                raise TestFailed(results)
    except Exception as e:
        raise TestFailed("Elasticsearch is not working. Exception %s ..." %e)

def test_consul(args):
    """
    Check if consul is working on system
    """
    try:
        Log.console("\n\n****************** Testing consul ***************************")
        db = Conf.get(const.DATABASE_INDEX, "databases")["consul_db"]["config"]
        url = "http://" + db["host"] + ":" + str(db["port"]) + "/v1/status/leader"
        if process_request(url).status_code != 200:
            raise
    except:
        raise TestFailed("Consul is not working ...")

test_list = [ test_statsd, test_kibana, test_elasticsearch, test_consul ]
