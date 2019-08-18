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
from csm.common.comm import SSHChannel, AmqpComm
from csm.common.log import Log
from csm.test.common import Const, TestFailed
from csm.common.cluster import Cluster, Node
from csm.core.blogic.alerts.alerts import AlertMonitor
from csm.eos.plugins.alert import AlertPlugin
import json, time
import filecmp

actual_count = 0
expected_count = 2

def init(args):
    args['amqp_client'] = AmqpComm()

def send_recv(args):
    client = args['amqp_client']
    client.init()
    with open('alert_input.json', 'r') as json_file:
        dict = json.load(json_file)
    for data in dict:
        client.send(data)
    with open('alert_output.json', 'w+') as json_file:
        json_file.write('[\n')
        json_file.close()
    args['objAlert'] = AlertPlugin()
    args['objAlert'].init(callback_fn=consume_alert)

def consume_alert(message):
    global actual_count
    global expected_count
    actual_count = actual_count + 1
    with open('alert_output.json', 'a+') as json_file:
        json.dump(json.loads(message), json_file, indent=4)
        if actual_count == expected_count:
            json_file.write('\n]')
        else:
            json_file.write(',\n')
        json_file.close()
    return True 

def test1(args):
    """
    Test case to match the count of alerts
    """
    send_recv(args)
    time.sleep(2)
    global actual_count
    global expected_count
    if actual_count != expected_count:
        raise TestFailed('Alerts count do not match.%d,%d'%(actual_count, expected_count))

def test2(args):
    args['objAlert'].stop()
    compare_results()

def compare_results():
    if not filecmp.cmp('alert_input.json', 'alert_output.json'):
        raise TestFailed('Input and Output alerts do not match.')

test_list = [ test1, test2 ]
