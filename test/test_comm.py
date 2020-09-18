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

import sys, os, getpass, socket, filecmp

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.comm import SSHChannel, AmqpComm
from cortx.utils.log import Log
from csm.test.common import Const, TestFailed
from csm.common.cluster import Cluster, Node
import json, time

client = None
file_path = Const.MOCK_PATH

def init(args):
    args[Const.CLUSTER] = Cluster(args[Const.INVENTORY_FILE])
    global client
    client = args['amqp_client']

def test1(args):
    """ SSH Command """

    for node in args['cluster'].node_list():
        channel = SSHChannel(node.host_name(), node.user())
        channel.connect()
        cmd = "ls -l /tmp"
        rc, output = channel.execute(cmd)
        channel.disconnect()
        Log.debug('rc=%d, output=%s' %(rc, output))
        if rc != 0:
            raise TestFailed('remote command failed to execute')

def test2(args):
    """ SSH Command (Invalid) """

    for node in args['cluster'].node_list():
        channel = SSHChannel(node.host_name(), node.user())
        channel.connect()
        cmd = "ls -l /invalid_path"
        rc, output = channel.execute(cmd)
        channel.disconnect()
        Log.debug('rc=%d, output=%s' %(rc, output))
        if rc == 0:
            raise TestFailed('invalid command returned 0')

def test3(args):
    """ SSH Copy """

    for node in args['cluster'].node_list():
        channel = SSHChannel(node.host_name(), node.user(), True)
        channel.connect()
        channel.recv_file("/etc/hosts", "/tmp/hosts")
        channel.send_file("/tmp/hosts", "/tmp/hosts1")
        channel.disconnect()
        if not filecmp.cmp("/etc/hosts", "/tmp/hosts1"):
            raise TestFailed('File Copy failed')

def amqp_callback(body):
    with open(file_path + 'output.text', 'w+') as json_file:
        json.dump(json.loads(body), json_file, indent=4)
        json_file.close()
        compare_results()
        global client
        client.acknowledge()
        client.stop()

def compare_results():
    if not filecmp.cmp(file_path + 'input.text', file_path + 'output.text'):
        raise TestFailed('Input and Output alerts do not match.')

def send_recv(args):
    """ Receive alerts from RMQ Channel """

    global client
    client.init() 
    with open(file_path + 'input.text') as json_file:
        data = json.load(json_file)
        client.send(data)
    client.recv(amqp_callback)

def test4(args):
    send_recv(args)

test_list = [ test1, test2, test3, test4 ]
