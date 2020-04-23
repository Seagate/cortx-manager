#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          ha_framework.py
 Description:       HAFramework manages resources.

 Creation Date:     02/08/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
import os
import time
import crypt
from csm.common.process import SimpleProcess
from csm.common.payload import JsonMessage
from csm.core.blogic import const
from csm.common.conf import Conf
from csm.common.log import Log


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

class PcsHAFramework(HAFramework):
    def __init__(self, resource_agents=None):
        super(PcsHAFramework, self).__init__(resource_agents)
        self._resource_agents = resource_agents
        self._user = const.NON_ROOT_USER
        self._password = const.NON_ROOT_USER_PASS

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
        Log.debug((f"executing command :- "
        f"{const.HCTL_NODE.format(command='status', user=self._user, pwd='********')}"))
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
            _standby_cmd = const.HCTL_NODE.format(command=_command,
                          user=self._user, pwd=self._password)
            Log.debug((f"executing command :- "
           f"{const.HCTL_NODE.format(command='status',user=self._user, pwd='********')}"))
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
            _unstandby_cmd = const.HCTL_NODE.format(command=_command,
                          user=self._user, pwd=self._password)
            Log.debug((f"executing command :- "
           f"{const.HCTL_NODE.format(command='status', user=self._user, pwd='********')}"))
            _proc = SimpleProcess(_unstandby_cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _rc != 0:
                raise Exception(_err)
            node = "all nodes" if node == "all" else node
            return { "message": const.STATE_CHANGE.format(node=node, state='passive')}
        except Exception as e:
            raise Exception("Failed to remove %s from passive state. Error: %s" %(node,e))

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
        _command = 'shutdown '
        _command = f"{_command} --all" if node == "all" else f"{_command} {node}"
        _cluster_shutdown_cmd = const.HCTL_NODE.format(command=_command,
                          user=self._user, pwd=self._password)
        _proc = SimpleProcess(_cluster_shutdown_cmd)
        _output, _err, _rc = _proc.run(universal_newlines=True)
        if _rc != 0:
            raise Exception(_err)
        result = f"{node} Shutdown Successful."
        return {"message": result}

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