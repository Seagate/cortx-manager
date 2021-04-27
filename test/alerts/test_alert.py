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
from csm.common.comm import MessageBusComm
from csm.test.common import TestFailed
from csm.plugins.cortx.alert import AlertPlugin
from csm.test.common import Const
import json, time
import filecmp
import threading
from unittest import mock

actual_count = 0
expected_count = 1
count_test2 = 0
file_path = Const.MOCK_PATH

permissions = {
"alerts": { "list": True, "update": True, "delete": True }
}

def init(args):
    args['message_bus_client'] = MessageBusComm()
    args['alert_plugin_test1'] = AlertPlugin()
    args['thread_test1'] = threading.Thread(target=recv_alerts_test1, args=(args, ))

def send_alerts(args):
    client = args['message_bus_client']
    client.init(type='producer', producer_id='csm_test_producer', \
            message_type='alerts', method='sync')
    global expected_count
    with open(file_path + 'alert_input.json', 'r') as json_file:
        dict = json.load(json_file)
    messages = []
    for data in dict:
        messages.append(json.dumps(data))
    client.send(messages)

def recv_alerts_test1(args):
    args['alert_plugin_test1'].init(callback_fn=consume_alert_test1, health_plugin=None)
    args['alert_plugin_test1'].process_request(cmd='listen')

def consume_alert_test1(message):
    global actual_count
    actual_count = actual_count + 1
    return True

def test1(args):
    """
    Test case to match the count of alerts
    """
    send_alerts(args)
    time.sleep(2)
    args['thread_test1'].start()
    time.sleep(2)
    global actual_count
    global expected_count
    if actual_count != expected_count:
        args['alert_plugin_test1'].stop()
        args['thread_test1'].join(timeout=2.0)
        raise TestFailed('Alerts count do not match. Actual : %d,\
                Excepcted :%d' %(actual_count, expected_count))
    args['alert_plugin_test1'].stop()
    args['thread_test1'].join(timeout=2.0)

test_list = [test1]
