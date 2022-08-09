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

from cortx.utils.log import Log
from csm.common.plugin import CsmPlugin
from csm.common.certificate import SSLCertificate
from csm.core.blogic import const
#TODO: Uncomment after integration
from cortx.utils.query_deployment import QueryDeployment
from cortx.utils.query_deployment.error import QueryDeploymentError
from csm.common.errors import CsmInternalError
from cortx.utils.conf_store.conf_store import Conf


class QueryDeploymentPlugin(CsmPlugin):
    """
    Communicates with utils framework for fetching
    deployment topology.
    """
    def __init__(self):
        """
        Initialize query deployment plugin
        """
        # set valid resources along with their attributes.
        self.valid_resources = {'clusters':['id', 'version', 'nodes', 'storage_set', 'certificates']}

    def init(self, **kwargs):
        pass

    @Log.trace_method(Log.DEBUG)
    def process_request(self, **kwargs):
        pass

    def _get_certificate_details(self, input_payload):
        """
        Get Certificate details
        """
        #TODO: Add device certificate/domain certificate once available.
        path = input_payload.get(const.SECURITY).get(const.SSL_CERTIFICATE)
        cert_details = SSLCertificate(path).get_certificate_details()
        cert_details = cert_details.get(const.CERT_DETAILS)
        cert_details[const.PATH] = path
        cert_details[const.TYPE] = "SSL Certificate"
        return [cert_details]

    def _create_node_payload(self, node):
        """
        Create payload for given node
        """
        # TODO: Use get method
        payload = {}
        payload[const.ID] = node.get(const.MACHINE_ID)
        payload[const.HOSTNAME] = node.get(const.HOSTNAME)
        payload[const.VERSION] = node.get(const.VERSION)
        payload[const.DEPLOYMENT_TIME] = node.get(const.DEPLOYMENT_TIME)
        payload[const.TYPE] = node.get(const.TYPE)
        payload[const.COMPONENTS] = node.get(const.COMPONENTS)
        if node.get(const.CVG):
            payload[const.CVG] = node.get(const.CVG)
        return payload

    def _get_nodes(self, input_payload, cluster_id):
        """
        Get node details specific to cluster
        """
        nodes = input_payload.get(const.NODES)
        res = []
        for node in nodes:
            if node.get(const.CLUSTER_ID) == cluster_id:
                res.append(self._create_node_payload(node))
        return res

    def _get_storage_set(self, payload):
        """
        Get storage_set details specific to cluster
        """
        return [{const.ID:item[const.NAME], const.DURABILITY:item[const.DURABILITY]} \
            for item in payload]

    def _create_cluster_payload(self, resource, valid_attributes, input_payload):
        """
        Generate payload for clusters.
        """
        Log.debug(f'Creating payload for resource: {resource}')
        res  = []
        total_clusters = input_payload[const.CLUSTER]
        for cluster in total_clusters:
            partial_payload = {}
            for attribute in valid_attributes:
                if attribute == const.ID:
                    partial_payload[attribute] = cluster.get(attribute)
                elif attribute == const.STORAGE_SET:
                    partial_payload[attribute] = self._get_storage_set(cluster[attribute])
                elif attribute == const.NODES:
                    cluster_id = cluster[const.ID]
                    partial_payload[attribute] = self._get_nodes(input_payload, cluster_id)
                elif attribute == const.CERTIFICATES:
                    partial_payload[attribute] = self._get_certificate_details(cluster)
                elif attribute == const.VERSION:
                    partial_payload[attribute] = input_payload.get(const.CORTX).\
                        get(const.COMMON).get(const.RELEASE).get(const.VERSION)
            res.append(partial_payload)
        return res

    def create_resource_payload(self, resource, input_payload):
        """
        Create payload body for each resource.
        """
        # Create payload based on specific resource and its schema.
        if resource == const.CLUSTERS:
            return self._create_cluster_payload(resource, self.valid_resources[resource], input_payload)

    def get_resource_payload(self, input_payload):
        """
        Get payload for all valid resource
        """
        resources_payload = {}
        for resource in self.valid_resources:
            resources_payload[resource] = self.create_resource_payload(resource, input_payload)
            return resources_payload

    def convert_schema(self, input_payload):
        """
        Covert schema of payload
        """
        coverted_payload = self.get_resource_payload(input_payload)
        res_payload = {}
        res_payload[const.TOPOLOGY] = coverted_payload
        return res_payload

    def validate_input(self, topology):
        # TODO: validation will be taken in future sprint
        pass

    def _get_url(self):
        """
        Get url for fetching topology.
        """
        host = Conf.get(const.DATABASE_INDEX, const.CONSUL_CONFIG_HOST)
        port = Conf.get(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_PORT)
        index = Conf.get(const.CSM_GLOBAL_INDEX, const.TOPOLOGY_INDEX)
        backend = Conf.get(const.CSM_GLOBAL_INDEX, const.TOPOLOGY_BACKEND)
        return f"{backend}://{host}:{port}/{index}"

    def get_topology(self):
        """
        Get topology of deployment
        """
        try:
            topology = QueryDeployment.get_cortx_topology(self._get_url())
            res = self.convert_schema(topology)
            self.validate_input(res)
        except QueryDeploymentError as e:
            Log.error(f'QueryDeployment error: {e}')
            raise CsmInternalError(f"Unable to fetch topology")
        except Exception as e:
            Log.error(f'{const.UNKNOWN_ERROR}: e')
            raise CsmInternalError(f"Unable to fetch topology")
        return res
