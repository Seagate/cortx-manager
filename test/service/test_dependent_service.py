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
import requests
# Package pika removed from csm
# Todo: Code clean up will be covered in future sprint
import pika
import random

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf

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
        host = Conf.get(const.CSM_GLOBAL_INDEX, "STATS>PROVIDER>host")
        port = Conf.get(const.CSM_GLOBAL_INDEX, "STATS>PROVIDER>port")
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
        hosts = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL>hosts")
        username = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL>username")
        password = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL>password")
        virtual_host = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL>virtual_host")
        ampq_hosts = [f'amqp://{username}:{password}@{host}/{virtual_host}' \
                      for host in hosts]
        ampq_hosts = [pika.URLParameters(host) for host in ampq_hosts]
        random.shuffle(ampq_hosts)
        connection = pika.BlockingConnection(ampq_hosts)
        channel = connection.channel()
        connection.close()
    except:
        raise TestFailed("RabbitMQ is not working ...")

test_list = [ test_statsd, test_kibana, test_elasticsearch, test_consule, test_rabbitmq ]
