#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_alert.py
 description:       Alert Infrastructure tests

 Creation Date:     17/08/2019
 Author:            Pawan Kumar Srivastava

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os, getpass, socket, filecmp

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.comm import AmqpComm
from csm.test.common import TestFailed
from csm.eos.plugins.alert import AlertPlugin
import json, time
import filecmp
import json
import threading

actual_count = 0
expected_count = 2
count_test2 = 0

def init(args):
    args['amqp_client'] = AmqpComm()
    args['alert_plugin_test1'] = AlertPlugin()
    args['alert_plugin_test2'] = AlertPlugin()
    args['thread_test1'] = threading.Thread(target=recv_alerts_test1,\
                                    args=(args, ))
    args['thread_test2'] = threading.Thread(target=recv_alerts_test2,\
                                    args=(args, ))

def send_alerts(args):
    client = args['amqp_client']
    client.init()
    global expected_count
    with open('alert_input.json', 'r') as json_file:
        dict = json.load(json_file)
    """ Creating CSM Schema Output for COmparision """
    with open('alert_output_expected.json', 'w+') as out_file:
        out_file.write('[\n')
        out_file.close()
    count = 0
    for data in dict:
        count = count + 1
        with open('alert_output_expected.json', 'a+') as out_file:
            message = create_output_schema(data)
            json.dump(message, out_file, indent=4)
            if count == expected_count:
                out_file.write('\n]')
            else:
                out_file.write(',\n')
            out_file.close()
        client.send(data)
        
def create_output_schema(msg_body):
    """ 
    Parsing the alert JSON to create the output schema
    """
    data = {'$schema': 'http://json-schema.org/draft-03/schema#', 'id':\
            'http://json-schema.org/draft-03/schema#', 'title':\
            'CSM HW Schema', 'type': 'object', 'properties':\
            {'header': {}, 'hw': {}}}
    
    dict = msg_body['message']['sensor_response_type']
    for values in dict.values():
        data['properties']['header'] = {'type': 'hw', 'alert_type': '%s'\
                %(values.get('alert_type', "")), 'type': 'hw', 'status':\
                '%s' %(values.get('info', {}).get('status', '')),\
                'resolved': 'no', 'acknowledged': 'no', 'description':\
                '%s' %(values.get('info', {}).get('health-reason', '')),\
                 'location': '%s' %(values.get('info', {}).get('location',\
                 '')), 'severity': '1', 'recommendation': '%s'\
                 %(values.get('info', {}).get('health-recommendation', ''))}
        data['properties']['hw'] = {'vendor': '%s' %(values.get('info', {})\
                .get('vendor', '')), 'enclosure_id': '%s'\
                %(values.get('info', {}).get('enclosure-id', '')), \
                'serial_number': '%s' %(values.get('info', {})\
                .get('serial-number', '')), 'part_number': '%s'\
                %(values.get('info', {}).get('part-number', ''))}
    return data

def recv_alerts_test1(args):
    args['alert_plugin_test1'].init(callback_fn=consume_alert_test1)
    args['alert_plugin_test1'].process_request(cmd='listen')

def recv_alerts_test2(args):
    with open('alert_output.json', 'w+') as json_file:
        json_file.write('[\n')
        json_file.close()
    args['alert_plugin_test2'].init(callback_fn=consume_alert_test2)
    args['alert_plugin_test2'].process_request(cmd='listen')

def consume_alert_test1(message):
    global actual_count
    actual_count = actual_count + 1
    return True 

def consume_alert_test2(message):
    global count_test2
    global expected_count
    count_test2 = count_test2 + 1
    with open('alert_output.json', 'a+') as json_file:
        json.dump(message, json_file, indent=4)
        if count_test2 == expected_count:
            json_file.write('\n]')
        else:
            json_file.write(',\n')
        json_file.close()
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

def compare_results():
    if not filecmp.cmp('alert_output_expected.json', 'alert_output.json'):
        raise TestFailed('Input and Output alerts do not match.')

test_list = [ test1, test2 ]
