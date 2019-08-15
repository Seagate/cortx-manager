#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_comm.py
 description:       SSH, AMQP Communication Reference

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

import sys, os, getpass, socket, filecmp

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.comm import SSHChannel, AmqpComm
from csm.common.log import Log
from csm.test.common import Const, TestFailed
from csm.common.cluster import Cluster, Node
import json, time

def init(args):
    args[Const.CLUSTER] = Cluster(args[Const.INVENTORY_FILE])

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

def amqp_callback(ct, ch, method, properties, body):
    with open('output.text', 'w') as json_file:
        json.dump(json.loads(body), json_file)
        json_file.close()
        compare_results()
        ch.basic_cancel(consumer_tag=ct)

def compare_results():
    if not filecmp.cmp('input.text', 'output.text'):
        raise TestFailed('Input and Output alerts do not match.')

def test4(args):
    """ Receive alerts from RMQ Channel"""

    amqp_client = AmqpComm()
    amqp_client.init()  
    with open('input.text') as json_file:
        data = json.load(json_file)
        amqp_client.send(data)
    amqp_client.recv(amqp_callback)
    amqp_client.listen()

test_list = [ test1, test2, test3, test4 ]
