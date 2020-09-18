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

import subprocess
import getpass
import yaml
import errno

from csm.core.blogic import const
from csm.common.errors import CsmError
from cortx.utils.log import Log

class Node(object):
    """ Contains all the attributes of the nodes.  """

    def __init__(self, host_name, node_type, sw_list, admin_user):
        self._host_name = host_name
        self._type = node_type
        self._sw_list = sw_list
        self._user = getpass.getuser()
        self._admin_user = admin_user
        self._active = True  # TODO - return state based on ssh connectivity

    def __str__(self):
        return '%s: %s %s %s' %(self._host_name, self._user, self._type, self._sw_list)

    def admin_user(self):
        return self._admin_user

    def user(self):
        """ Returns admin user name """
        return self._user

    def sw_components(self):
        """ Returns a list of components. """
        return self._sw_list

    def host_name(self):
        return self._host_name

    def node_type(self):
        return self._type

    def is_active(self):
        # TODO - return state based on ssh connectivity
        return self._active


class Cluster(object):
    """
    This class handles cluster/node related operations.
    Common responsibility includes,
    1. Discovery of all the nodes or only SSUs in the cluster.
    2. Communication with any/all the nodes in the cluster.

    Cluster inventory file follows yaml format:
    -----------------------------------------------
    SSU:
        sw_components: [ os, motr, hare ]
        nodes: [ ssu_1, ssu_2 ]

    S3_SERVER:
        sw_components: [ os, motr, hare ]
        nodes: [ s3_1, s3_2 ]

    CMU:
        sw_components: [ os ]
        nodes: [ cmu ]
    -----------------------------------------------
    """

    def __init__(self, inventory_file, ha_framework):
        self._inventory = yaml.safe_load(open(inventory_file).read())
        self._node_list = {}
        self._ha_framework = ha_framework
        for node_type in self._inventory.keys():
            if const.KEY_COMPONENTS not in self._inventory[node_type].keys():
                raise CsmError(errno.EINVAL,
                    'invalid cluster configuration. No components for type %s' %node_type)

            if const.KEY_NODES not in self._inventory[node_type].keys():
                raise CsmError(errno.EINVAL,
                    'invalid cluster configuration. No nodes for type %s' %node_type)
            if const.ADMIN_USER not in self._inventory[node_type].keys():
                raise CsmError(errno.EINVAL,
                    'invalid cluster configuration. No admin user for type %s' %node_type)

            sw_components = self._inventory[node_type][const.KEY_COMPONENTS]
            admin_user = self._inventory[node_type][const.ADMIN_USER]
            for node_id in self._inventory[node_type][const.KEY_NODES]:
                if node_id not in self._node_list.keys():
                    node = Node(node_id, node_type, sw_components, admin_user)
                    self._node_list[node_id] = node

    def init(self, force_flag):
        self._ha_framework.init(force_flag)

    def node_list(self, node_type=None):
        """ Nodes of specified type """
        if node_type == None:
            return [ self._node_list[x] for x in self._node_list.keys() ]
        return [ self._node_list[x] for x in self._node_list.keys() \
            if self._node_list[x].node_type() == node_type ]

    def host_list(self, node_type=None):
        """ Returns the list of all SSUs in the cluster.  """
        if node_type == None:
            return [ self._node_list[x].host_name() for x in self._node_list.keys() ]
        return [ self._node_list[x].host_name()  for x in self._node_list.keys() \
            if self._node_list[x].node_type() == node_type ]

    def sw_components(self, node_type):
        """ Returns a list of components. """
        return self._inventory[node_type][const.KEY_COMPONENTS]

    def active_node_list(self):
        """ Returns all the active nodes in the cluster """
        # TODO - Scan the list and identify reachable nodes
        return [ self._node_list[x] for x in self._node_list.keys() \
            if self._node_list[x].is_active() == True ]

    def state(self):
        """
            Return tuple containing two things:
            1. Cluster state, i.e. 'up', 'down' or 'degraded'
            2. List of active nodes
            3. List of inactive nodes
        """

        state = None
        active_node_list = []
        inactive_node_list = []
        for node in self._node_list:
            if node.is_active(): active_node_list.append(node)
            else: inactive_node_list.append(node)

        if len(active_node_list) == 0: state = const.STATE_DOWN
        elif len(inactive_node_list) == 0: state = const.STATE_UP
        else: state = const.STATE_DEGRADED

        return state, active_node_list, inactive_node_list

    def get_nodes(self):
        """
            Return following things
            1. List of active nodes
            2. List of inactive nodes
        """
        return self._ha_framework.get_nodes()

    def get_status(self):
        """
            Return if HAFramework in up or down
        """
        return self._ha_framework.get_status()
