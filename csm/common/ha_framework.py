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
import time
from importlib import import_module
from csm.common.errors import CsmNotFoundError, InvalidRequest
from csm.common.payload import JsonMessage
from csm.common.ha.cluster_management.operations_factory import ResourceOperationsFactory
from cortx.utils.cron import CronJob
from csm.core.blogic import const

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log


class HAFramework:
    """Base class that enables client interaction with the HA framework."""

    def __init__(self, resource_agents):
        """
        Initialize HA framework.

        :param resource_agents: list of resource agents.
        :returns: None.
        """
        self._resource_agents = resource_agents

    def init(self, force_flag):
        """
        HA framework's 'init' operation.

        :param force_flag: forcefully repeat 'init'.
        :returns: None.
        """
        # ToDo: This is not being used, need to revisit
        # if self.get_status() != 'up':
        #     raise Exception('Error: HA Framework is not initalized ...')
        for ra in self._resource_agents.values():
            if not ra.init(force_flag):
                raise Exception('Error: initalizing resource agent %s' % ra)
        return True

    def failover(self):
        pass

    # def is_available(self):
    #     pass
    
    # ToDo: This is not being used, need to revisit
    # def get_nodes(self):
    #     pass

    # ToDo: This is not being used, need to revisit
    # def get_status(self):
    #     pass


class CortxHAFramework(HAFramework):
    def __init__(self, resource_agents=None):
        super(CortxHAFramework, self).__init__(resource_agents)
        self._user = Conf.get(const.CSM_GLOBAL_INDEX, const.NON_ROOT_USER_KEY)
        self._cluster_manager = None
        self._cluster_elements = None

    # ToDo: This is not being used, need to revisit
    # def get_nodes(self):
    #     """Return the status of Cortx HA Cluster/Nodes."""
    #     online = False
    #     _live_node_cmd = const.CORTXHA_CLUSTER.format(command='status')
    #     Log.debug(f"executing command :- {_live_node_cmd}")
    #     _proc = SimpleProcess(_live_node_cmd)
    #     _output, _err, _rc = _proc.run(universal_newlines=True)
    #     if _rc not in [0, 1]:
    #         raise Exception("Failed: Command: %s Returncode: %s Error: %s" % (
    #             _live_node_cmd, _rc, _err))
    #     if _output and _output.lower().strip() == "online":
    #         online = True
    #     return {"node_status": [{"name": "cluster", "online": online,
    #                              "standby": not online}]}
    
    # ToDo: This is not being used, need to revisit
    # @staticmethod
    # def make_node_active(node):
    #     """Put node on standby node for maintenance use."""
    #     try:
    #         _start_cmd = const.HCTL_NODE.format(
    #             command=const.CORTXHA_CLUSTER.format(command="start"))
    #         Log.debug(f"executing command :-  {_start_cmd}")
    #         _proc = SimpleProcess(_start_cmd)
    #         _, _err, _rc = _proc.run(universal_newlines=True)
    #         if _rc not in [0, 1]:
    #             raise Exception(_err)
    #         return {"message": const.STATE_CHANGE.format(node="cluster",
    #                                                      state='start')}
    #     except Exception as e:
    #         raise Exception("Failed to put %s on active state. Error: %s" % (node, e))

    def shutdown(self, node):
        """Shutdown the current Cluster or Node."""
        _command = "{CSM_PATH}/scripts/cortxha_shutdown_cron.sh"
        _cluster_shutdown_cmd = _command.format(CSM_PATH=const.CSM_PATH)
        shutdown_cron_time = Conf.get(const.CSM_GLOBAL_INDEX,
                                      "MAINTENANCE>shutdown_cron_time")
        Log.info(f"Setting Cron Command with args ->  user : {self._user}")
        cron_job_obj = CronJob(self._user)
        cron_time = cron_job_obj.create_run_time(seconds=shutdown_cron_time)
        err_msg = (f"Setting Shutdown Cron at time -> {str(cron_time)}"
                   f"current system time {time.asctime()}")
        Log.info(err_msg)
        cron_job_obj.create_new_job(_cluster_shutdown_cmd,
                                    const.SHUTDOWN_COMMENT, cron_time)
        return {
            "message": f"Node shutdown will begin in {shutdown_cron_time} seconds."}

    def get_system_health(self, element='cluster', depth: int = 1, **kwargs):
        has_system_health = hasattr(self._cluster_manager, "get_system_health")
        if self._cluster_manager is None or not has_system_health:
            self._init_cluster_manager()

        self._validate_resource(element)
        parsed_system_health = None
        try:
            system_health = self._cluster_manager.get_system_health(element, depth,
                                                                    **kwargs)
            # TODO: Remove the statement below when delimiter issue is
            # fixed in cortx-utils.
            Conf.init(delim='>')
            Log.debug(f"HA Framework-System Health: {system_health}")
            parsed_system_health = JsonMessage(system_health).load()
        except Exception as e:
            err_msg = f"{const.HEALTH_FETCH_ERR_MSG} : {e}"
            Log.error(err_msg)
            raise Exception(err_msg)

        self._validate_system_health_response(parsed_system_health)

        return parsed_system_health[const.OUTPUT_LITERAL]

    def get_cluster_status(self, node_id):
        has_system_health = hasattr(self._cluster_manager, "get_system_health")
        if self._cluster_manager is None or not has_system_health:
            self._init_cluster_manager()

        cluster_status_resp = None
        try:
            cluster_status_resp_json = self._cluster_manager.node_controller\
                .check_cluster_feasibility(node_id)
            # TODO: Remove the statement below when delimiter issue is
            # fixed in cortx-utils.
            Conf.init(delim='>')
            Log.debug(f"HA Framework - Get Cluster Status: {cluster_status_resp_json}")
            cluster_status_resp = JsonMessage(cluster_status_resp_json).load()
        except Exception as e:
            Log.error(f"{const.CLUSTER_STATUS_ERR_MSG} : {e}")
            raise Exception(const.CLUSTER_STATUS_ERR_MSG)

        result = None
        if cluster_status_resp[const.STATUS_LITERAL] == const.STATUS_FAILED:
            result = {
                const.STATUS_LITERAL: const.WARNING,
                const.MESSAGE_LITERAL: const.CLUSTER_STATUS_WARN_MSG
            }
        elif cluster_status_resp[const.STATUS_LITERAL] == const.STATUS_SUCCEEDED:
            result = {
                const.STATUS_LITERAL: const.OK,
                const.MESSAGE_LITERAL: const.CLUSTER_STATUS_OK_MSG
            }

        return result

    def process_cluster_operation(self, resource, operation, **arguments):
        has_system_health = hasattr(self._cluster_manager, "get_system_health")
        if self._cluster_manager is None or not has_system_health:
            self._init_cluster_manager()

        self._validate_resource(resource)
        Log.debug(f"HA Framework - Cluster Operation: "
                  f"Requesting {operation} operation on {resource} with "
                  f"arguments {arguments}.")
        ResourceOperationsFactory.get_operations_by_resource(resource)\
            .get_operation(operation)\
            .process(self._cluster_manager, **arguments)
        # TODO: Remove the statement below when delimiter issue is
        # fixed in cortx-utils.
        Conf.init(delim='>')
        cluster_op_resp = {
            "message": f"{operation.capitalize()} request for {resource} is placed successfully."
        }
        Log.debug(f"HA Framework - Cluster Operation: {cluster_op_resp}")

        return cluster_op_resp

    def _init_cluster_manager(self):
        Log.info("Initializing CortxClusterManager")
        cortx_cluster_manager = import_module('ha.core.cluster.cluster_manager')
        ha_system_health_const = import_module('ha.core.system_health.const')

        try:
            self._cluster_manager = cortx_cluster_manager.CortxClusterManager(
                default_log_enable=False)
            self._cluster_elements = ha_system_health_const.CLUSTER_ELEMENTS
        except Exception as e:
            err_msg = f"Error instantiating CortxClusterManager: {e}"
            Log.error(err_msg)

    def _validate_resource(self, resource):
        unsupported_resource = True
        for supported_resource in self._cluster_elements:
            if resource == supported_resource.value:
                unsupported_resource = False
                break

        if unsupported_resource:
            raise CsmNotFoundError(f"Resource {resource} not found.")

    @staticmethod
    def _validate_system_health_response(system_health):
        if system_health is None:
            raise Exception(const.HEALTH_FETCH_ERR_MSG)

        if system_health[const.STATUS_LITERAL] == const.STATUS_FAILED:
            raise InvalidRequest(system_health[const.ERROR_LITERAL])


class PcsHAFramework(HAFramework):
    def __init__(self, resource_agents=None):
        super(PcsHAFramework, self).__init__(resource_agents)
        self._resource_agents = resource_agents
        self._user = Conf.get(const.CSM_GLOBAL_INDEX, const.NON_ROOT_USER_KEY)
        self._password = Conf.get(const.CSM_GLOBAL_INDEX, "CSM>password")

    # ToDo: This is not being used, need to revisit
    # def get_nodes(self):
    #     """
    #         Return tuple containing following things:
    #         1. List of active nodes
    #         2. List of inactive nodes
    #         Output:
    #         Corosync Nodes:
    #             Online: node1 node2
    #             Offline:
    #     """
    #     _live_node_cmd = const.HCTL_NODE.format(command='status',
    #                                             user=self._user, pwd=self._password)
    #     Log.debug(f"executing command :- "
    #               f"{const.HCTL_NODE.format(command='status',user=self._user, pwd='*****')}")
    #     _proc = SimpleProcess(_live_node_cmd)
    #     _output, _err, _rc = _proc.run(universal_newlines=True)
    #     if _rc != 0:
    #         raise Exception("Failed: Command: %s Returncode: %s Error: %s"
    #                         % (_live_node_cmd, _rc, _err))
    #     return {"node_status": JsonMessage(_output.strip()).load()}

    # ToDo: This is not being used, need to revisit
    # def make_node_active(self, node):
    #     """
    #         Put node on standby node for maintenance use
    #     """
    #     try:
    #         _command = 'unstandby '
    #         _command = f"{_command } --all" if node == "all" else f"{_command } {node}"
    #         Log.debug(f"executing command :-  "
    #                   f"{const.HCTL_NODE.format(command=_command, user=self._user, pwd='*****')}")
    #         _standby_cmd = const.HCTL_NODE.format(command=_command,
    #                                               user=self._user, pwd=self._password)
    #         _proc = SimpleProcess(_standby_cmd)
    #         _output, _err, _rc = _proc.run(universal_newlines=True)
    #         if _rc != 0:
    #             raise Exception(_err)
    #         node = "all nodes" if node == "all" else node
    #         return {"message": const.STATE_CHANGE.format(node=node, state='active')}
    #     except Exception as e:
    #         raise Exception("Failed to put %s on active state. Error: %s" % (node, e))

    # ToDo: This is not being used, need to revisit
    # def make_node_passive(self, node):
    #     """
    #         Put node on standby node for maintenance use
    #     """
    #     try:
    #         _command = 'standby '
    #         _command = f"{_command} --all" if node == "all" else f"{_command} {node}"
    #         Log.debug(f"executing command :-  "
    #                   f"{const.HCTL_NODE.format(command=_command, user=self._user, pwd='*****')}")

    #         _unstandby_cmd = const.HCTL_NODE.format(command=_command,
    #                                                 user=self._user, pwd=self._password)
    #         _proc = SimpleProcess(_unstandby_cmd)
    #         _output, _err, _rc = _proc.run(universal_newlines=True)
    #         if _rc != 0:
    #             raise Exception(_err)
    #         node = "all nodes" if node == "all" else node
    #         return {"message": const.STATE_CHANGE.format(node=node, state='passive')}
    #     except Exception as e:
    #         raise Exception("Failed to remove %s from passive state. Error: %s" % (node, e))

    # ToDo: This is not being used, need to revisit
    # def get_status(self):
    #     """
    #         Return if HAFramework in up or down
    #     """
    #     _cluster_status_cmd = "hctl cluster status"
    #     _proc = SimpleProcess(_cluster_status_cmd)
    #     _output, _err, _rc = _proc.run(universal_newlines=True)
    #     return 'down' if _err != '' else 'up'

    def shutdown(self, node):
        """
        Shutdown the current Cluster or Node.
        :return:
        """
        _command = "{CSM_PATH}/scripts/shutdown_cron.sh -u {user} -p {pwd} -n {node}"
        _cluster_shutdown_cmd = _command.format(node=node, user=self._user, pwd=self._password,
                                                CSM_PATH=const.CSM_PATH)
        shutdown_cron_time = Conf.get(const.CSM_GLOBAL_INDEX,
                                      "MAINTENANCE>shutdown_cron_time")
        Log.info(f"Setting Cron Command with args -> node : {node}, user : {self._user}")
        cron_job_obj = CronJob(self._user)
        cron_time = cron_job_obj.create_run_time(seconds=shutdown_cron_time)
        Log.info(f"Setting Shutdown Cron at time -> {str(cron_time)} "
                 f"current system time {time.asctime()}")
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

    # def is_available(self):
    #     pass


class PcsResourceAgent(ResourceAgent):
    def __init__(self, resources):
        super(PcsResourceAgent, self).__init__(resources)
        self._resources = resources

    # def is_available(self):
    #     """
    #         Return True if all resources available else False
    #     """
    #     for resource in self._resources:
    #         _chk_res_cmd = "pcs resource show " + resource
    #         _proc = SimpleProcess(_chk_res_cmd)
    #         _output, _err, _rc = _proc.run(universal_newlines=True)
    #         if _err != '':
    #             return False
    #     return True

    # def _delete_resource(self):
    #     for resource in self._resources:
    #         _delete_res_cmd = "pcs resource delete " + resource
    #         _proc = SimpleProcess(_delete_res_cmd)
    #         _output, _err, _rc = _proc.run(universal_newlines=True)
    #         if _err != '':
    #             raise Exception("Failed: Command: %s Error: %s Returncode: %s"
    #                             % (_delete_res_cmd, _err, _rc))

    def _ra_init(self):
        self._cmd_list = []
        self._resource_file = "/var/csm/ha/resource-loaded.conf"
        if not os.path.exists("/var/csm/ha"):
            os.makedirs("/var/csm/ha")
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
        self._cmd_list.append(f"pcs -f {self._resource_file} constraint "
                              f"colocation set {' '.join(self._resources)}")
        # Configure update
        self._cmd_list.append(f"pcs -f {self._resource_file} constraint "
                              f"order set {' '.join(self._resources)}")

        # Configure score
        for resource in self._resources:
            self._cmd_list.append(f'pcs -f {self._resource_file} constraint location {resource} '
                                  f'prefers {self._primary}={score}')
            self._cmd_list.append(f'pcs -f {self._resource_file} constraint location {resource} '
                                  f'prefers {self._secondary}={score}')

    # def _execute_config(self):
    #     self._cmd_list.append("pcs cluster cib-push " + self._resource_file)
    #     for cmd in self._cmd_list:
    #         _proc = SimpleProcess(cmd)
    #         _output, _err, _rc = _proc.run(universal_newlines=True)
    #         if _err != '':
    #             raise Exception("Failed: Command: %s Error: %s Returncode: %s" % (cmd, _err, _rc))
