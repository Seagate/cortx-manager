#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_dependent_service.py
 Description:       Test csm dependent service status.

 Creation Date:     07/08/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os
import time
import requests
import pika

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from eos.utils.log import Log
from csm.common.conf import Conf

def init(args):
    pass

def process_request(url):
    return requests.get(url)

def check_systemd_service(service):
    """
    Utility to check systemd service
    """
    Log.console('Testing %s service ...' %service)
    cmd = "systemctl is-active --quiet " + service
    status = os.system(cmd)
    if status != 0:
        raise TestFailed("%s service is not running..." %service)

#################
# Tests
#################
def test_statsd(args):
    """
    Check status for statsd service
    """
    check_systemd_service("statsd")

def test_kibana(args):
    """
    Check status for Kibana service
    """
    try:
        time.sleep(5)
        Log.console("Testing Kibana service")
        host = Conf.get(const.CSM_GLOBAL_INDEX, "STATS.PROVIDER.host")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "STATS.PROVIDER.port")
        url = "http://" + host + ":" + str(port)
        resp = process_request(url)
        if resp.status_code != 200:
            raise
    except:
        raise TestFailed("Kibana is not working ...")

def test_elasticsearch(args):
    """
    Check if elasticsearch is running on system
    """
    try:
        time.sleep(5)
        Log.console("Testing Elasticsearch service")
        db = Conf.get(const.DATABASE_INDEX, "databases")["es_db"]["config"]
        url = "http://" + db["host"] + ":" + str(db["port"])
        resp = process_request(url)
        if resp.status_code != 200:
            raise
    except:
        raise TestFailed("Elasticsearch is not working ...")

def test_consule(args):
    """
    Check if consul is working on system
    """
    try:
        Log.console("Testing consul service ...")
        db = Conf.get(const.DATABASE_INDEX, "databases")["consul_db"]["config"]
        url = "http://" + db["host"] + ":" + str(db["port"]) + "/v1/status/leader"
        if process_request(url).status_code != 200:
            raise
    except:
        raise TestFailed("Consul is not working ...")

def test_rabbitmq(args):
    """
    Check status for rabbitmq service
    """
    try:
        Log.console("Testing rabbitmq service")
        host = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.host")
        connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        channel = connection.channel()
        connection.close()
    except:
        raise TestFailed("RabbitMQ is not working ...")

test_list = [ test_statsd, test_kibana, test_elasticsearch, test_consule, test_rabbitmq ]
