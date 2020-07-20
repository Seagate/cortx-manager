#!/usr/bin/env python3
import argparse
import concurrent.futures
import random
import re
import threading
import time
from concurrent import futures

import paramiko
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

ES_DEPCOMMAND = [
"systemctl stop elasticsearch",
"yum remove -y elasticsearch",
"rm -rf /var/log/elasticsearch",
"rm -rf /var/log/data/elasticsearch",
"rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch",
"""tee /etc/yum.repos.d/elasticsearch.repo > /dev/null <<EOF
[elasticsearch]
name=Elasticsearch repository for 7.x packages
baseurl=https://artifacts.elastic.co/packages/7.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=0
autorefresh=1
type=rpm-md
EOF
""",
"yum install -y --enablerepo=elasticsearch elasticsearch",
"""tee /etc/elasticsearch/elasticsearch.yml > /dev/null <<EOF
# ======================== Elasticsearch Configuration =========================
#
# NOTE: Elasticsearch comes with reasonable defaults for most settings.
#       Before you set out to tweak and tune the configuration, make sure you
#       understand what are you trying to accomplish and the consequences.
#
# The primary way of configuring a node is via this file. This template lists
# the most important settings you may want to configure for a production cluster.
#
# Please consult the documentation for further information on configuration options:
# https://www.elastic.co/guide/en/elasticsearch/reference/index.html
#
# ---------------------------------- Cluster -----------------------------------
#
# Use a descriptive name for your cluster:
#
cluster.name: elasticsearch_cluster
#
# ------------------------------------ Node ------------------------------------
#
# Use a descriptive name for the node:
#
#node.name: node-1
#
# Add custom attributes to the node:
#
#node.attr.rack: r1
#
# ----------------------------------- Paths ------------------------------------
#
# Path to directory where to store the data (separate multiple locations by comma):
#
path.data: /var/log/data/elasticsearch
#
# Path to log files:
#
path.logs: /var/log/elasticsearch
#
# ----------------------------------- Memory -----------------------------------
#
# Lock the memory on startup:
#
#bootstrap.memory_lock: true
#
# Make sure that the heap size is set to about half the memory available
# on the system and that the owner of the process is allowed to use this
# limit.
#
# Elasticsearch performs poorly when the system is swapping the memory.
#
# ---------------------------------- Network -----------------------------------
#
# Set the bind address to a specific IP (IPv4 or IPv6):
#
network.host: 0.0.0.0
#
# Set a custom port for HTTP:
#
http.port: 9200
#
# For more information, consult the network module documentation.
#
# --------------------------------- Discovery ----------------------------------
#
# Pass an initial list of hosts to perform discovery when this node is started:
# The default list of hosts is ["127.0.0.1", "[::1]"]
#
discovery.seed_hosts: [{0}]
#
# Bootstrap the cluster using an initial set of master-eligible nodes:
#
cluster.initial_master_nodes: [{0}]
#
# For more information, consult the discovery and cluster formation module documentation.
#
# ---------------------------------- Gateway -----------------------------------
#
# Block initial recovery after a full cluster restart until N nodes are started:
#
#gateway.recover_after_nodes: 3
#
# For more information, consult the gateway module documentation.
#
# ---------------------------------- Various -----------------------------------
#
# Require explicit names when deleting indices:
#
#action.destructive_requires_name: true
EOF
""",
"mkdir -p /var/log/data/elasticsearch",
"chown elasticsearch:elasticsearch /var/log/data/elasticsearch",
"chmod 750 /var/log/data/elasticsearch",
"systemctl daemon-reload",
"systemctl enable elasticsearch",
"systemctl start elasticsearch"]

"""
#java -version
#openjdk version "1.8.0_242"
#OpenJDK Runtime Environment (build 1.8.0_242-b08)
#OpenJDK 64-Bit Server VM (build 25.242-b08, mixed mode)
"""

def runcmd(client, cmd):
	stdin, stdout, stderr = client.exec_command(f"sudo {cmd}", get_pty=True)
	time.sleep(1)
	stdin.write(f"{args.password}\n")
	stdin.flush()
	for line in stdout:
		print(line.strip('\n'))
	for line in stderr:
		print(line.strip('\n'))

def es_deploy(host):
	LOCAL_ES_DEPCOMMAND	= ES_DEPCOMMAND.copy()
	LOCAL_ES_DEPCOMMAND[7]=LOCAL_ES_DEPCOMMAND[7].format(', '.join([f'"{x["name"]}"' for x in vms]))
	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(host, username=args.user, password=args.password)
	for s in LOCAL_ES_DEPCOMMAND:
		runcmd(client,s)
	client.close()
	return 0

def get_token():
	r = requests.get(url=f"{args.url}api/auth", verify=False, auth = (args.user, args.password))
	if r.status_code != 200: 
		print("Fatal: Request status code != 200")
		exit(-1)
	return r.json()["auth_token"]

def request_vm():
	print("Requesting VM")
	url = f"{args.url}api/service_catalogs/1000000000002/service_templates/1000000000040"
	payload = '{"action" : "order", "resource" : {"href" : "' + args.url \
		+ 'api/service_templates/1000000000002","dialog_check_box_1": "t","extra_disk_count": "2","extra_disk_size": "50","share_vms_disks": "t" }}'
	headers = {'X-Auth-Token': args.auth_token}
	r = requests.request("POST", url, headers=headers, data = payload, verify=False)
	if r.status_code != 200: 
		print("Fatal: Request status code != 200")
		exit(-1)
	return r.json()["id"]
	
	
def check_r_code(r):
	if r.status_code != 200: 
		print("Fatal: Request status code != 200")
		exit(-1)

def get_request_vm_name(request_id):
	request_state = ""
	while request_state != "finished":
		r = requests.request("GET", url = f"{args.url}api/service_requests/{request_id}?expand=resources,request_tasks", headers={'X-Auth-Token': args.auth_token}, verify=False)
		check_r_code(r)
		status = r.json()["status"]
		request_state= r.json()["request_state"]
		print(f"status:{status} request_state:{request_state}")
		if request_state != "finished":
			time.sleep(5)
	if status != "Ok":
		print("Fatal: status is not Ok")
		exit(-1)
	
	for i in r.json()["request_tasks"]:
		if "vm_target_hostname" in i["options"]:
			print(i["options"]["vm_target_hostname"] + "." + i["options"]["dns_domain"] + "VMID")
			return i["options"]["vm_target_hostname"] + "." + i["options"]["dns_domain"]

def request_3vms():
	local_vms = [request_vm(),request_vm(),request_vm()]
	args.hosts = ','.join([get_request_vm_name(x) for x in local_vms]) 
	print("New VMs: " + args.hosts)

def get_vm_ids():
	r = requests.request("GET", url=f"{args.url}api/vms", headers = {'X-Auth-Token': args.auth_token}, verify=False)
	check_r_code(r)
	for x in r.json()["resources"]:
		rvm = requests.request("GET", url=x["href"], headers = {'X-Auth-Token': args.auth_token}, verify=False)
		check_r_code(rvm)
		for y in vms:
			l = len(rvm.json()["name"])
			if y["name"][:l] == rvm.json()["name"]:
				y["vm_id"] = rvm.json()["id"]

def scan_vm(vm_id):
	r = requests.post(f"{args.url}api/vms/{vm_id}", '{"action": "scan"}', headers = {'X-Auth-Token': args.auth_token},verify=False)
	assert(r.json()["success"])
	check_r_code(r)

def start_vm(vm_id):
	print(f"Starting VM {vm_id}")
	r = requests.post(f"{args.url}api/vms/{vm_id}", '{"action": "start"}', headers = {'X-Auth-Token': args.auth_token},verify=False)
	assert(r.json()["success"])
	check_r_code(r)

def stop_vm(vm_id):
	print(f"Stoping VM {vm_id}")
	r = requests.post(f"{args.url}api/vms/{vm_id}", '{"action": "stop"}', headers = {'X-Auth-Token': args.auth_token},verify=False)
	assert(r.json()["success"])
	check_r_code(r)

def get_vm_power_state(vm_id):
	r = requests.get(f"{args.url}api/vms/{vm_id}", headers = {'X-Auth-Token': args.auth_token},verify=False)
	check_r_code(r)
	return r.json()["power_state"] == "on"

def get_vm_power_states():
	for x in vms:
		scan_vm(x["vm_id"])
	time.sleep(5)
	for x in vms:
		x["power"] = get_vm_power_state(x["vm_id"])

def start_all_vms():
	get_vm_power_states()
	b = False
	for x in vms:
		if not x["power"]:
			start_vm(x["vm_id"])
			b = True
	if b:
		time.sleep(80)

def start_es_deploy():
	start_all_vms()
	start = time.time()
	ex = futures.ThreadPoolExecutor(max_workers=len(vms))
	results = ex.map(es_deploy, [x["name"] for x in vms])
	real_results = list(results)
	end = time.time()
	print(f"DONE in {end - start} sec")

def get_node_shard(query_node):
	for x in vms:
		x["pr"] = None
	r = requests.get(f'http://{query_node}:9200/_cat/shards/test_index')
	check_r_code(r)
	for x in r.text.splitlines():
		for y in vms:
			if len(x.split()) >= 8:
				if x.split()[7] == y["name"]:
					y["pr"] = x.split()[2]

def get_node_shards():
	get_vm_power_states()
	for x in vms:
		if x["power"]:
			get_node_shard(x["name"])
			break
	else:
		assert(False)

def stop_primary_node():
	get_node_shards()
	for x in vms:
		if x["pr"] == "p":
			stop_vm(x["vm_id"])
			break
	else:
		assert(False)
	time.sleep(70)


def test_1():
	start_all_vms()
	requests.delete(f'http://{vms[0]["name"]}:9200/test_index')
	check_r_code(requests.put(f'http://{vms[1]["name"]}:9200/test_index',
							  '{"settings" : {"number_of_replicas" : 2, "auto_expand_replicas" : "2-all"}}',
							  headers = {'Content-Type': 'application/json'}))
	r = requests.put(f'http://{vms[0]["name"]}:9200/test_index/_doc/1',
				 '{"name": "Doc1"}',
				 headers = {'Content-Type': 'application/json'})
	assert(r.status_code == 201)
	time.sleep(15)
	stop_primary_node()
	get_node_shards()
	for y in vms:
		if y["pr"]=="p":
			check_r_code(requests.put(f'http://{y["name"]}:9200/test_index/_doc/1',
				 '{"name": "Doc2"}',
				 headers = {'Content-Type': 'application/json'}))
			break
	else:
		assert(False)
	start_all_vms()
	time.sleep(15)
	stop_primary_node()
	get_node_shards()
	for y in vms:
		if y["pr"] == "p":
			r = requests.get(f'http://{y["name"]}:9200/test_index/_doc/1')
			if r.json()["_source"]["name"] == "Doc2":
				print('TEST PASSED')
			else:
				print('TEST FAILED')
			break
	else:
		assert(False) 

parser = argparse.ArgumentParser()
parser.add_argument('--url', help='Cloud URL', required=True, )
parser.add_argument('--user', help='Username GID', required=True)
parser.add_argument('--password', help='Password', required=True)
parser.add_argument('--commands', help='Commands divided by comma. They will be executed in the following order: request_3vms,deploy_es,test_es', required=True)
parser.add_argument('--auth_token', help='Authorization token for SSC.')
parser.add_argument('--hosts', help='Host names divided by comma')

args = parser.parse_args()

if "request_3vms" not in args.commands and not args.hosts: 
	print("Hosts are not specified. Exiting")
	exit(-1)

if not args.auth_token: 
	args.auth_token = get_token()

if "request_3vms" in args.commands:
	request_3vms()

vms = [{"name": x, "req_id": None, "vm_id": None, "pr": None, "power": None} for x in args.hosts.split(",")]
get_vm_ids()

if "deploy_es" in args.commands:
	start_es_deploy()

if "test_es" in args.commands:
	test_1()