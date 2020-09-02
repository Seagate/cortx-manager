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
from csm.common.comm import AmqpComm
from csm.test.common import TestFailed
from csm.plugins.cortx.alert import AlertPlugin
from csm.test.common import Const
import json, time
import filecmp
import threading
from unittest import mock

actual_count = 0
expected_count = 2
count_test2 = 0
file_path = Const.MOCK_PATH

permissions = {
"alerts": { "list": True, "update": True, "delete": True }
}

def init(args):
    args['amqp_client'] = AmqpComm()
    args['alert_plugin_test1'] = AlertPlugin()
    args['alert_plugin_test2'] = AlertPlugin()
    args['alert_plugin_test3'] = AlertPlugin()
    args['thread_test1'] = threading.Thread(target=recv_alerts_test1, args=(args, ))
    args['thread_test2'] = threading.Thread(target=recv_alerts_test2, args=(args, ))
    args['thread_test3'] = threading.Thread(target=recv_alerts_test3, args=(args,))

def send_alerts(args):
    client = args['amqp_client']
    client.init()
    global expected_count
    with open(file_path + 'alert_input.json', 'r') as json_file:
        dict = json.load(json_file)
    """ Creating CSM Schema Output for COmparision """
    with open('alert_output_expected.json', 'w+') as out_file:
        out_file.write('[\n')
        out_file.close()
    count = 0
    for data in dict:
        count = count + 1
        with open(file_path + 'alert_output_expected.json', 'a+') as out_file:
            message = AlertPlugin()._convert_to_csm_schema(json.dumps(data))
            message.pop("updated_time")
            json.dump(message, out_file, indent=4)
            if count == expected_count:
                out_file.write('\n]')
            else:
                out_file.write(',\n')
            out_file.close()
        client.send(data)

def recv_alerts_test1(args):
    args['alert_plugin_test1'].init(callback_fn=consume_alert_test1)
    args['alert_plugin_test1'].process_request(cmd='listen')

def recv_alerts_test2(args):
    with open(file_path + 'alert_output.json', 'w+') as json_file:
        json_file.write('[\n')
        json_file.close()
    args['alert_plugin_test2'].init(callback_fn=consume_alert_test2)
    args['alert_plugin_test2'].process_request(cmd='listen')

def recv_alerts_test3(args):
    args['alert_plugin_test3'].init(callback_fn=consume_alert_test1)
    args['alert_plugin_test3'].process_request(cmd='listen')

def consume_alert_test1(message):
    global actual_count
    actual_count = actual_count + 1
    return True 

def consume_alert_test2(message):
    global count_test2
    global expected_count
    count_test2 = count_test2 + 1
    message.pop("updated_time")
    with open(file_path + 'alert_output.json', 'a+') as json_file:
        json.dump(message, json_file, indent=4)
        if count_test2 == expected_count:
            json_file.write('\n]')
        else:
            json_file.write(',\n')
        json_file.close()
    return True 

def transmit_method(args):
    class Mock:
        async def handle_event(self, alert_data):
            return None
    args['alert_plugin_test3']._decision_maker = Mock()

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
        raise TestFailed('Alerts count do not match. Actual : %d,\
                Excepcted :%d' %(actual_count, expected_count))
    args['alert_plugin_test1'].stop()
    args['thread_test1'].join()


def test2(args):
    send_alerts(args)
    time.sleep(2)
    args['thread_test2'].start()
    time.sleep(2)
    compare_results()
    args['alert_plugin_test2'].stop()
    args['thread_test2'].join()

def test3(args):
    send_alerts(args)
    time.sleep(2)
    args['thread_test3'].start()
    time.sleep(2)
    args['alert_plugin_test3'].stop()
    args['thread_test3'].join()

def compare_results():
    if not filecmp.cmp(file_path + 'alert_output_expected.json',
                        file_path + 'alert_output.json'):
        raise TestFailed('Input and Output alerts do not match.')

test_list = [ test1, test2, test3]
