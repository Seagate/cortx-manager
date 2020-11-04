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

import filecmp
import json

from cortx.utils.log import Log

from csm.common.cluster import Cluster
from csm.common.comm import SSHChannel
from csm.common.conf import Conf
from csm.common.ha_framework import PcsHAFramework
from csm.core.blogic import const
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.test.common import Const, TestFailed

client = None
file_path = Const.MOCK_PATH


def init(args):
    csm_resources = Conf.get(const.CSM_GLOBAL_INDEX, "HA.resources")
    csm_ra = {"csm_resource_agent": CsmResourceAgent(csm_resources)}
    ha_framework = PcsHAFramework(csm_ra)
    args['cluster'] = Cluster(args[Const.INVENTORY_FILE], ha_framework)
    global client  # pylint: disable=global-statement
    client = args['amqp_client']


def test1(args):
    """SSH Command"""
    for node in args['cluster'].node_list():
        channel = SSHChannel(node.host_name(), node.user())
        channel.connect()
        cmd = "ls -l /tmp"
        rc, output = channel.execute(cmd)
        channel.disconnect()
        Log.debug('rc=%d, output=%s' % (rc, output))
        if rc != 0:
            raise TestFailed('remote command failed to execute')


def test2(args):
    """SSH Command (Invalid)"""
    for node in args['cluster'].node_list():
        channel = SSHChannel(node.host_name(), node.user())
        channel.connect()
        cmd = "ls -l /invalid_path"
        rc, output = channel.execute(cmd)
        channel.disconnect()
        Log.debug('rc=%d, output=%s' % (rc, output))
        if rc == 0:
            raise TestFailed('invalid command returned 0')


def test3(args):
    """SSH Copy"""
    for node in args['cluster'].node_list():
        channel = SSHChannel(node.host_name(), node.user(), True)
        channel.connect()
        channel.recv_file("/etc/hosts", "/tmp/hosts")
        channel.send_file("/tmp/hosts", "/tmp/hosts1")
        channel.disconnect()
        if not filecmp.cmp("/etc/hosts", "/tmp/hosts1"):
            raise TestFailed('File Copy failed')


def amqp_callback(body):
    with open(f"{file_path}output.text", 'w+') as json_file:
        json.dump(json.loads(body), json_file, indent=4)
        json_file.close()
        compare_results()
        global client  # pylint: disable=global-statement
        client.acknowledge()
        client.stop()


def compare_results():
    if not filecmp.cmp(f"{file_path}input.text", f"{file_path}output.text"):
        raise TestFailed('Input and Output alerts do not match.')


def send_recv():
    """Receive alerts from RMQ Channel"""
    global client  # pylint: disable=global-statement
    client.init()
    with open(f"{file_path}input.text") as json_file:
        data = json.load(json_file)
        client.send(data)
    client.recv(amqp_callback)


def test4():
    send_recv()


test_list = [test1, test2, test3, test4]
