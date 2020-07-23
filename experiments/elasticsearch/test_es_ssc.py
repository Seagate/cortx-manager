#!/usr/bin/env python3
import argparse
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
    LOCAL_ES_DEPCOMMAND = ES_DEPCOMMAND.copy()
    LOCAL_ES_DEPCOMMAND[7] = LOCAL_ES_DEPCOMMAND[7].format(', '.join([f'"{x["name"]}"' for x in vms]))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=args.user, password=args.password)
    for depoloy_command in LOCAL_ES_DEPCOMMAND:
        runcmd(client, depoloy_command)
    client.close()
    return 0


def get_token():
    req = requests.get(url=f"{args.url}api/auth", verify=False, auth=(args.user, args.password))
    if req.status_code != 200:
        print("Fatal: Request status code != 200")
        exit(-1)
    return req.json()["auth_token"]


def request_vm():
    print("Requesting VM")
    url = f"{args.url}api/service_catalogs/1000000000002/service_templates/1000000000040"
    payload = '{"action" : "order", "resource" : {"href" : "' + args.url \
        + 'api/service_templates/1000000000002","dialog_check_box_1": "t","extra_disk_count": "2","extra_disk_size": "50","share_vms_disks": "t" }}'
    headers = {'X-Auth-Token': args.auth_token}
    req = requests.request("POST", url, headers=headers, data=payload, verify=False)
    if req.status_code != 200:
        print("Fatal: Request status code != 200")
        exit(-1)
    return req.json()["id"]


def check_r_code(req):
    if req.status_code != 200:
        print("Fatal: Request status code != 200")
        exit(-1)


def get_request_vm_name(request_id):
    request_state = ""
    while request_state != "finished":
        req = requests.get(
            url=f"{args.url}api/service_requests/{request_id}?expand=resources,request_tasks",
            headers={'X-Auth-Token': args.auth_token},
            verify=False)
        check_r_code(req)
        status = req.json()["status"]
        request_state = req.json()["request_state"]
        print(f"status:{status} request_state:{request_state}")
        if request_state != "finished":
            time.sleep(5)
    if status != "Ok":
        print("Fatal: status is not Ok")
        exit(-1)

    for tasks in req.json()["request_tasks"]:
        if "vm_target_hostname" in tasks["options"]:
            print(tasks["options"]["vm_target_hostname"] + "." + tasks["options"]["dns_domain"] + "VMID")
            return tasks["options"]["vm_target_hostname"] + "." + tasks["options"]["dns_domain"]


def request_3vms():
    local_vms = [request_vm(), request_vm(), request_vm()]
    args.hosts = ','.join([get_request_vm_name(x) for x in local_vms])
    print("New VMs: " + args.hosts)


def get_vm_ids():
    req = requests.request("GET", url=f"{args.url}api/vms", headers={'X-Auth-Token': args.auth_token}, verify=False)
    check_r_code(req)
    for resource in req.json()["resources"]:
        rvm = requests.request("GET", url=resource["href"], headers={'X-Auth-Token': args.auth_token}, verify=False)
        check_r_code(rvm)
        for y in vms:
            l_var = len(rvm.json()["name"])
            if y["name"][:l_var] == rvm.json()["name"]:
                y["vm_id"] = rvm.json()["id"]


def scan_vm(vm_id):
    req = requests.post(f"{args.url}api/vms/{vm_id}", '{"action": "scan"}', headers={'X-Auth-Token': args.auth_token}, verify=False)
    assert(req.json()["success"])
    check_r_code(req)


def start_vm(vm_id):
    print(f"Starting VM {vm_id}")
    req = requests.post(f"{args.url}api/vms/{vm_id}", '{"action": "start"}', headers={'X-Auth-Token': args.auth_token}, verify=False)
    assert(req.json()["success"])
    check_r_code(req)


def stop_vm(vm_id):
    print(f"Stoping VM {vm_id}")
    req = requests.post(f"{args.url}api/vms/{vm_id}", '{"action": "stop"}', headers={'X-Auth-Token': args.auth_token}, verify=False)
    assert(req.json()["success"])
    check_r_code(req)


def get_vm_power_state(vm_id):
    req = requests.get(f"{args.url}api/vms/{vm_id}", headers={'X-Auth-Token': args.auth_token}, verify=False)
    check_r_code(req)
    return req.json()["power_state"] == "on"


def get_vm_power_states():
    for vm in vms:
        scan_vm(vm["vm_id"])
    time.sleep(5)
    for vm in vms:
        vm["power"] = get_vm_power_state(vm["vm_id"])


def start_all_vms():
    get_vm_power_states()
    timeout_needed = False
    for vm in vms:
        if not vm["power"]:
            start_vm(vm["vm_id"])
            timeout_needed = True
    if timeout_needed:
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
    for vm in vms:
        vm["pr"] = None
    req = requests.get(f'http://{query_node}:9200/_cat/shards/test_index')
    check_r_code(req)
    for machine in req.text.splitlines():
        for vm in vms:
            if len(machine.split()) >= 8:
                if machine.split()[7] == vm["name"]:
                    vm["pr"] = machine.split()[2]


def get_node_shards():
    get_vm_power_states()
    for vm in vms:
        if vm["power"]:
            get_node_shard(vm["name"])
            break
    else:
        assert(False)


def stop_primary_node():
    get_node_shards()
    for vm in vms:
        if vm["pr"] == "p":
            stop_vm(vm["vm_id"])
            break
    else:
        assert(False)
    time.sleep(70)


def test_1():
    start_all_vms()
    requests.delete(f'http://{vms[0]["name"]}:9200/test_index')
    check_r_code(requests.put(f'http://{vms[1]["name"]}:9200/test_index',
                              '{"settings" : {"number_of_replicas" : 2, "auto_expand_replicas" : "2-all"}}',
                              headers={'Content-Type': 'application/json'}))
    req = requests.put(f'http://{vms[0]["name"]}:9200/test_index/_doc/1',
                       '{"name": "Doc1"}',
                       headers={'Content-Type': 'application/json'})
    assert(req.status_code == 201)
    time.sleep(15)
    stop_primary_node()
    get_node_shards()
    for vm in vms:
        if vm["pr"] == "p":
            check_r_code(requests.put(
                f'http://{vm["name"]}:9200/test_index/_doc/1',
                '{"name": "Doc2"}',
                headers={'Content-Type': 'application/json'}))
            break
    else:
        assert(False)
    start_all_vms()
    time.sleep(15)
    stop_primary_node()
    get_node_shards()
    for vm in vms:
        if vm["pr"] == "p":
            req = requests.get(f'http://{vm["name"]}:9200/test_index/_doc/1')
            if req.json()["_source"]["name"] == "Doc2":
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
