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

import os
import random
import time

import pika
import requests
from cortx.utils.log import Log

from csm.common.conf import Conf
from csm.core.blogic import const
from csm.test.common import TestFailed


def process_request(url):
    return requests.get(url)


def check_systemd_service(service):
    """Utility to check systemd service"""
    Log.console('Testing %s service ...' % service)
    cmd = f"systemctl is-active --quiet {service}"
    status = os.system(cmd)
    if status != 0:
        raise TestFailed("%s service is not running..." % service)

#################
# Tests
#################


def test_statsd():
    """Check status for statsd service"""
    check_systemd_service("statsd")


def test_kibana():
    """Check status for Kibana service"""
    time.sleep(5)
    Log.console("Testing Kibana service")
    host = Conf.get(const.CSM_GLOBAL_INDEX, "STATS.PROVIDER.host")
    port = Conf.get(const.CSM_GLOBAL_INDEX, "STATS.PROVIDER.port")
    url = f"http://{host}:{port}"
    resp = process_request(url)
    if resp.status_code != 200:
        raise TestFailed("Kibana is not working ...")


def test_elasticsearch():
    """Check if elasticsearch is running on system"""
    time.sleep(5)
    Log.console("Testing Elasticsearch service")
    db = Conf.get(const.DATABASE_INDEX, "databases")["es_db"]["config"]
    url = f'http://{db["host"]}:{db["port"]}'
    resp = process_request(url)
    if resp.status_code != 200:
        raise TestFailed("Elasticsearch is not working ...")


def test_consul():
    """Check if consul is working on system"""
    Log.console("Testing consul service ...")
    db = Conf.get(const.DATABASE_INDEX, "databases")["consul_db"]["config"]
    url = f'http://{db["host"]}:{db["port"]}/v1/status/leader'
    if process_request(url).status_code != 200:
        raise TestFailed("Consul is not working ...")


def test_rabbitmq():
    """Check status for rabbitmq service"""
    Log.console("Testing rabbitmq service")
    hosts = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.hosts")
    username = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.username")
    password = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.password")
    virtual_host = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.virtual_host")
    ampq_hosts = [f'amqp://{username}:{password}@{host}/{virtual_host}' for host in hosts]
    ampq_hosts = [pika.URLParameters(host) for host in ampq_hosts]
    random.shuffle(ampq_hosts)
    connection = pika.BlockingConnection(ampq_hosts)
    connection.channel()
    connection.close()


test_list = [test_statsd, test_kibana, test_elasticsearch, test_consul, test_rabbitmq]
