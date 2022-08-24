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
from csm.common.certificate import SSLCertificate
from pathlib import Path
from cortx.utils.conf_store.error import ConfError

class ITopology(metaclass=ABCMeta):
    "The Topology Interface (Product)"

    @staticmethod
    @abstractmethod
    def get():
        "A static interface method"
        pass

class CortxTopology(ITopology):
    "The CortxTopology Concrete Class implements the ITopology interface"

    def __init__(self, url):
        self.url = url
        # Set valid resources along with their attributes.
        self.valid_resources = {'cluster':['id', 'version', 'nodes', 'storage_sets', 'certificates']}

    def _get_services(self, components):
        """
        get services provided by all components for given node.
        """
        services = []
        for component in components:
            if component.get('services'):
                services.extend(component.get('services'))
        return services

    def _create_node_payload(self, node_id, node):
        """
        Create payload for given node
        """
        payload = {}
        payload[const.ID] = node_id
        payload[const.VERSION] = node.get(const.PROVISIONING).get(const.VERSION)
        services = self._get_services(node[const.COMPONENTS])
        if services:
            payload[const.SERVICES] = services
        payload[const.TYPE] = node.get(const.TYPE)
        payload[const.STORAGE_SET] = node.get(const.STORAGE_SET)
        payload[const.DEPLOYMENT_TIME] = node.get(const.PROVISIONING).get(const.TIME)
        payload[const.HOSTNAME] = node.get(const.HOSTNAME)
        if node.get(const.CVG):
            for cvg in node.get(const.CVG):
                cvg[const.DEVICES] = {key: value for key, value \
                    in cvg[const.DEVICES].items() if not ('num_' in key)}
            payload[const.STORAGE] = node.get(const.CVG)
        return payload

    def _get_nodes(self, input_payload, cluster_id):
        """
        Get node details specific to cluster
        """
        nodes = input_payload.get(const.NODE)
        res = []
        for node_id in nodes.keys():
            if nodes.get(node_id).get(const.CLUSTER_ID) == cluster_id:
                res.append(self._create_node_payload(node_id, nodes.get(node_id)))
        return res

    def _get_storage_set(self, payload):
        """
        Get storage_set details specific to cluster
        """
        def _get_durability(payload):
            const.DIX = payload.get(const.DIX)
            const.SNS = payload.get(const.SNS)
            res = {
                const.DATA: f"{const.DIX.get(const.DATA)}+{const.DIX.get(const.PARITY)}"\
                            f"+{const.DIX.get(const.SPARE)}",
                const.METADATA: f"{const.SNS.get(const.DATA)}+{const.SNS.get(const.PARITY)}"\
                            f"+{const.SNS.get(const.SPARE)}"
            }
            return res
        return [{const.ID:item[const.NAME], const.DURABILITY:_get_durability(item[const.DURABILITY])} \
            for item in payload]

    def _get_certificate_details(self, input_payload):
        """
        Get Certificate details
        """
        #TODO: Add device certificate/domain certificate once available.
        path = input_payload.get(const.CORTX).get(const.COMMON).get(const.SECURITY).get(const.SSL_CERTIFICATE)
        cert_details = SSLCertificate(path).get_certificate_details()
        cert_details = cert_details.get(const.CERT_DETAILS)
        cert_details[const.NAME] = Path(path).name
        cert_details[const.TYPE] = "SSL Certificate"
        return [cert_details]

    def _create_cluster_payload(self, resource, valid_attributes, input_payload):
        """
        Generate payload for cluster with required attributes.
        """
        Log.debug(f'Creating payload for resource: {resource}')
        cluster = input_payload[const.CLUSTER]
        payload = {}
        for attribute in valid_attributes:
            if attribute == const.ID:
                payload[attribute] = cluster.get(attribute)
            elif attribute == const.STORAGE_SETS:
                payload[attribute] = self._get_storage_set(cluster[const.STORAGE_SET])
            elif attribute == const.NODES:
                cluster_id = cluster[const.ID]
                payload[attribute] = self._get_nodes(input_payload, cluster_id)
            elif attribute == const.CERTIFICATES:
                payload[attribute] = self._get_certificate_details(input_payload)
            elif attribute == const.VERSION:
                payload[attribute] = input_payload.get(const.CORTX).\
                    get(const.COMMON).get(const.RELEASE).get(const.VERSION)
        return payload

    def create_resource_payload(self, resource, input_payload):
        """
        Create payload body for each resource.
        """
        # Create payload based on specific resource and its schema.
        if resource == const.CLUSTER:
            return self._create_cluster_payload(resource, self.valid_resources[resource], input_payload)

    def get_resource_payload(self, input_payload):
        """
        Get payload for all valid resource
        """
        resources_payload = {}
        for resource in self.valid_resources:
            resources_payload[resource] = self.create_resource_payload(resource, input_payload)
            return resources_payload

    def _convert(self, input_payload):
        """
        Convert topology payload schema to specific format.
        """
        coverted_payload = self.get_resource_payload(input_payload)
        res_payload = {}
        res_payload[const.TOPOLOGY] = coverted_payload
        return res_payload

    def _get_topology(self):
        """
        get toplogy payload from current deployment.
        """
        try:
            Conf.load(const.TOPOLOGY_DICT_INDEX, 'dict:{"k":"v"}')
        except ConfError:
            Log.debug(f"index {const.TOPOLOGY_DICT_INDEX} is already loaded")
        Conf.copy(const.CONSUMER_INDEX, const.TOPOLOGY_DICT_INDEX)
        payload = {
            const.CLUSTER : Conf.get(const.TOPOLOGY_DICT_INDEX, const.CLUSTER),
            const.CORTX : Conf.get(const.TOPOLOGY_DICT_INDEX, const.CORTX),
            const.NODE : Conf.get(const.TOPOLOGY_DICT_INDEX, const.NODE)
        }
        return payload

    def get(self):
        """
        get topology for cortx
        """
        orignal_payload = self._get_topology()
        payload  = self._convert(orignal_payload)
        return payload

class TopologyFactory:
    "The Factory Class"
    def get_instance(config):
        "A method to get a instance of specific topology"
        # TODO: CHANGE name "backend to more appropriate one"
        topology = {
                const.CORTX : CortxTopology(config.get(const.URL))
        }
        obj_topology = topology[config.get(const.BACKEND)]
        return obj_topology