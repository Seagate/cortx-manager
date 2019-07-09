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

import sys, os
import subprocess

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
    def __init__(self, resource_agents):
        super(PcsHAFramework, self).__init__(resource_agents)
        self._resource_agents = resource_agents

    def get_nodes(self):
        """
            Return tuple containing following things:
            1. List of active nodes
            2. List of inactive nodes
        """
        _livenode_cmd = ["/usr/sbin/pcs", "status", "nodes", "corosync"]
        _output = str(subprocess.check_output(_livenode_cmd, stderr=subprocess.PIPE))
        _status_list = _output.split("\\n")
        _activenodes = _status_list[1].split()
        _activenodes.pop(0)
        _inactivenodes = _status_list[2].split()
        _inactivenodes.pop(0)
        return _activenodes, _inactivenodes

    def get_status(self):
        """
            Return if HAFramework in up or down
        """
        _cluster_status_cmd = ["/usr/sbin/pcs", "cluster", "status"]
        _rc = subprocess.run(_cluster_status_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'up' if _rc.returncode == 0 else 'down'

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
            _chk_res_cmd = ["pcs", "resource", "show", resource]
            _rc = subprocess.run( _chk_res_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            if _rc.returncode != 0:
                return False
        return True

    def _delete_resource(self):
        for resource in self._resources:
            _delete_res_cmd = ["pcs", "resource", "delete", resource]
            _rc = subprocess.run( _delete_res_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            if _rc.returncode != 0:
                raise Exception("Failed to delete resource %s" %resource)

    def _ra_init(self):
        self._cmd_list = []
        self._resource_file = "/var/tmp/resource.conf"
        self._cmd_list.append("pcs cluster cib " + self._resource_file)
        if not os.path.exists("/var/tmp"): os.makedirs("/var/tmp")

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
        FNULL = open(os.devnull, 'w')
        for cmd in self._cmd_list:
            subprocess.check_call(cmd.split(), stdout=FNULL, stderr=subprocess.PIPE)
