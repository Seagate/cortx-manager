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

import sys
import os
import time
import crypt
from csm.common.process import SimpleProcess
from csm.common.payload import JsonMessage
from cortx.utils.cron import CronJob
from csm.core.blogic import const

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log


class HAFramework:
    def __init__(self, resource_agents):
        self._resource_agents = resource_agents

    def init(self, force_flag):
        _results = []
        if self.get_status() != 'up':
            raise Exception('Error: HA Framework is not initalized ...')
        for ra in self._resource_agents.values():
            if not ra.init(force_flag):
                raise Exception('Error: initalizing resource agent %s' %ra)
        return True

    def failover(self):
        pass

    def is_available(self):
        pass

    def get_nodes(self):
        pass

    def get_status(self):
        pass

class CortxHAFramework(HAFramework):
    def __init__(self, resource_agents = None):
        super(CortxHAFramework, self).__init__(resource_agents)
        self._user = const.NON_ROOT_USER

    def get_nodes(self):
        """Return the status of Cortx HA Cluster/Nodes."""
        online = False
        _live_node_cmd = const.CORTXHA_CLUSTER.format(command = 'status')
        Log.debug(f"executing command :- {_live_node_cmd}")
        _proc = SimpleProcess(_live_node_cmd)
        _output, _err, _rc = _proc.run(universal_newlines = True)
        if _rc not in [0, 1]:
            raise Exception("Failed: Command: %s Returncode: %s Error: %s" % (
                _live_node_cmd, _rc, _err))
        if _output and _output.lower().strip() == "online":
            online = True
        return {"node_status": [{"name": "cluster", "online": online,
                                 "standby": not online}]}

    def make_node_active(self, node):
        """Put node on standby node for maintenance use."""
        try:
            _start_cmd = const.HCTL_NODE.format(
                command = const.CORTXHA_CLUSTER.format(command="start"))
            Log.debug(f"executing command :-  {_start_cmd}")
            _proc = SimpleProcess(_start_cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _rc not in [0, 1]:
                raise Exception(_err)
            return {"message": const.STATE_CHANGE.format(node="cluster",
                                                          state='start')}
        except Exception as e:
            raise Exception("Failed to put %s on active state. Error: %s" %(node,e))

    def shutdown(self, node):
        """Shutdown the current Cluster or Node."""
        _command = "{CSM_PATH}/scripts/cortxha_shutdown_cron.sh"
        _cluster_shutdown_cmd = _command.format(CSM_PATH = const.CSM_PATH)
        shutdown_cron_time = Conf.get(const.CSM_GLOBAL_INDEX,
                                      "MAINTENANCE.shutdown_cron_time")
        Log.info(f"Setting Cron Command with args ->  user : {self._user}")
        cron_job_obj = CronJob(self._user)
        cron_time = cron_job_obj.create_run_time(seconds=shutdown_cron_time)
        Log.info(f"Setting Shutdown Cron at time -> {str(cron_time)} current system time {time.asctime()}")
        cron_job_obj.create_new_job(_cluster_shutdown_cmd,
                                    const.SHUTDOWN_COMMENT, cron_time)
        return {
            "message": f"Node shutdown will begin in {shutdown_cron_time} seconds."}


class PcsHAFramework(HAFramework):
    def __init__(self, resource_agents=None):
        super(PcsHAFramework, self).__init__(resource_agents)
        self._resource_agents = resource_agents
        self._user = const.NON_ROOT_USER
        self._password = Conf.get(const.CSM_GLOBAL_INDEX, "CSM.password")

    def get_nodes(self):
        """
            Return tuple containing following things:
            1. List of active nodes
            2. List of inactive nodes
            Output:
            Corosync Nodes:
                Online: node1 node2
                Offline:
        """
        _live_node_cmd = const.HCTL_NODE.format(command='status',
                        user=self._user, pwd=self._password)
        Log.debug(f"executing command :- "
              f"{const.HCTL_NODE.format(command='status',user=self._user, pwd='*****')}")
        _proc = SimpleProcess(_live_node_cmd)
        _output, _err, _rc = _proc.run(universal_newlines=True)
        if _rc != 0:
            raise Exception("Failed: Command: %s Returncode: %s Error: %s"
                            %(_live_node_cmd, _rc, _err))
        return {"node_status": JsonMessage(_output.strip()).load()}

    def make_node_active(self, node):
        """
            Put node on standby node for maintenance use
        """
        try:
            _command = 'unstandby '
            _command = f"{_command } --all" if node == "all" else f"{_command } {node}"
            Log.debug(f"executing command :-  "
              f"{const.HCTL_NODE.format(command=_command, user=self._user, pwd='*****')}")
            _standby_cmd = const.HCTL_NODE.format(command=_command,
                          user=self._user, pwd=self._password)
            _proc = SimpleProcess(_standby_cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _rc != 0:
                raise Exception(_err)
            node = "all nodes" if node == "all" else node
            return { "message": const.STATE_CHANGE.format(node=node, state='active')}
        except Exception as e:
            raise Exception("Failed to put %s on active state. Error: %s" %(node,e))

    def make_node_passive(self, node):
        """
            Put node on standby node for maintenance use
        """
        try:
            _command = 'standby '
            _command = f"{_command} --all" if node == "all" else f"{_command} {node}"
            Log.debug(f"executing command :-  "
              f"{const.HCTL_NODE.format(command=_command, user=self._user, pwd='*****')}")

            _unstandby_cmd = const.HCTL_NODE.format(command=_command,
                          user=self._user, pwd=self._password)
            _proc = SimpleProcess(_unstandby_cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _rc != 0:
                raise Exception(_err)
            node = "all nodes" if node == "all" else node
            return { "message": const.STATE_CHANGE.format(node=node, state='passive')}
        except Exception as e:
            raise Exception("Failed to remove %s from passive state. Error: %s" %(node, e))

    def get_status(self):
        """
            Return if HAFramework in up or down
        """
        _cluster_status_cmd = "hctl cluster status"
        _proc = SimpleProcess(_cluster_status_cmd)
        _output, _err, _rc = _proc.run(universal_newlines=True)
        return 'down' if _err != '' else 'up'

    def shutdown(self, node):
        """
        Shutdown the current Cluster or Node.
        :return:
        """
        _command = "{CSM_PATH}/scripts/shutdown_cron.sh -u {user} -p {pwd} -n {node}"
        _cluster_shutdown_cmd = _command.format(node=node,
                          user=self._user, pwd=self._password, CSM_PATH=const.CSM_PATH)
        shutdown_cron_time = Conf.get(const.CSM_GLOBAL_INDEX,
                                       "MAINTENANCE.shutdown_cron_time")
        Log.info(f"Setting Cron Command with args -> node : {node}, user : {self._user}")
        cron_job_obj = CronJob(self._user)
        cron_time = cron_job_obj.create_run_time(seconds=shutdown_cron_time)
        Log.info(f"Setting Shutdown Cron at time -> {str(cron_time)} current system time {time.asctime()}")
        cron_job_obj.create_new_job(_cluster_shutdown_cmd, const.SHUTDOWN_COMMENT, cron_time)
        return {"message": f"Node shutdown will begin in {shutdown_cron_time} seconds."}

class ResourceAgent:
    def __init__(self, resources):
        self._resources = resources

    def init(self, force_flag):
        pass

    def get_state(self):
        pass

    def failover(self):
        pass

    def is_available(self):
        pass

class PcsResourceAgent(ResourceAgent):
    def __init__(self, resources):
        super(PcsResourceAgent, self).__init__(resources)
        self._resources = resources

    def is_available(self):
        """
            Return True if all resources available else False
        """
        for resource in self._resources:
            _chk_res_cmd = "pcs resource show " + resource
            _proc = SimpleProcess(_chk_res_cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _err != '':
                return False
        return True

    def _delete_resource(self):
        for resource in self._resources:
            _delete_res_cmd = "pcs resource delete " + resource
            _proc = SimpleProcess(_delete_res_cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _err != '':
                raise Exception("Failed: Command: %s Error: %s Returncode: %s"
                                %(_delete_res_cmd, _err, _rc))

    def _ra_init(self):
        self._cmd_list = []
        self._resource_file = "/var/tmp/resource.conf"
        if not os.path.exists("/var/tmp"): os.makedirs("/var/tmp")
        self._cmd_list.append("pcs cluster cib " + self._resource_file)

    def _init_resource(self, resource, service, provider, interval, timeout):
        _cmd = "pcs -f " + self._resource_file + " resource create " + resource +\
            " " + provider + ":" + service + " meta failure-timeout=10s" +\
            " op monitor timeout=" + timeout[1] + " interval=" + interval[1] +\
            " op start timeout=" + timeout[0] + " interval=" + interval[0] +\
            " op stop timeout=" + timeout[2] + " interval=" + interval[2]
        self._cmd_list.append(_cmd)

    def _init_constraint(self, score):
        # Configure colocation
        self._cmd_list.append("pcs -f " + self._resource_file +\
            " constraint colocation set " + ' '.join(self._resources))

        # Configure update
        self._cmd_list.append("pcs -f " + self._resource_file +\
            " constraint order set " + ' '.join(self._resources))

        # Configure score
        for resource in self._resources:
            self._cmd_list.append("pcs -f " + self._resource_file +\
                " constraint location " + resource + " prefers " +\
                self._primary + "=" + score)
            self._cmd_list.append("pcs -f " + self._resource_file +\
                " constraint location " + resource + " prefers " +\
                self._secondary + "=" + score)

    def _execute_config(self):
        self._cmd_list.append("pcs cluster cib-push " + self._resource_file)
        for cmd in self._cmd_list:
            _proc = SimpleProcess(cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _err != '':
                raise Exception("Failed: Command: %s Error: %s Returncode: %s" %(cmd, _err, _rc))