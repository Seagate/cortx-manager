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

from abc import ABCMeta, abstractmethod
from cortx.utils.log import Log
from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf

class ITopology(metaclass=ABCMeta):
    "The Topology Interface (Product)"

    @staticmethod
    @abstractmethod
    def get():
        pass
        "A static interface method"

class CortxTopology(ITopology):
    "The CortxTopology Concrete Class implements the ITopology interface"

    def __init__(self, url):
        self.url = url

    def _map(self):
        pass

    def _convert(self):
        """
        Convert topology schema to specific format
        """
        pass

    def _get_deployment_topology(self):
        """
        get toplogy payload from current deployment.
        """
        Conf.load(const.TOPOLOGY_DICT_INDEX, 'dict:{"k":"v"}')
        Conf.copy(const.CONSUMER_INDEX, const.TOPOLOGY_DICT_INDEX)
        payload = {
            const.CLUSTER : Conf.get(const.TOPOLOGY_DICT_INDEX, const.CLUSTER),
            const.CORTX : Conf.get(const.TOPOLOGY_DICT_INDEX, const.CORTX),
            const.NODE : Conf.get(const.TOPOLOGY_DICT_INDEX, const.NODE)
        }

    def get(self):
        """
        get topology for cortx
        """
        orignal_payload = self._get_deployment_topology()
        payload  = self._convert(orignal_payload)
        return payload

class TopologyFactory:
    "The Factory Class"
    def get_instance(config):
        "A static method to get a instance of specific topology"
        # TODO: CHANGE name "backend to more appropriate one"
        topology = {
                const.CORTX : CortxTopology(config.get(const.url))
        }
        topology_instance = topology[config.get(const.BACKEND)]
        return topology_instance
