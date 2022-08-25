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
from csm.common.errors import CsmInternalError, CsmNotFoundError

class ITopology(metaclass=ABCMeta):
    "The Topology Interface"

    @staticmethod
    @abstractmethod
    def get(self):
        "A static interface method"
        pass

class CortxTopology(ITopology):
    "The CortxTopology Concrete Class implements the ITopology interface"

    def __init__(self, url):
        self.url = url

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
        payload = dict()
        payload[const.ID] = node_id
        if node.get(const.PROVISIONING):
            payload[const.VERSION] = node.get(const.PROVISIONING).get(const.VERSION)
        services = self._get_services(node[const.COMPONENTS])
        if services:
            payload[const.SERVICES] = services
        payload[const.TYPE] = node.get(const.TYPE)
        payload[const.STORAGE_SET] = node.get(const.STORAGE_SET)
        if node.get(const.PROVISIONING):
            payload[const.DEPLOYMENT_TIME] = node.get(const.PROVISIONING).get(const.TIME)
        payload[const.HOSTNAME] = node.get(const.HOSTNAME)
        if node.get(const.CVG):
            for cvg in node.get(const.CVG):
                cvg[const.DEVICES] = {key: value for key, value \
                    in cvg[const.DEVICES].items() if not ('num_' in key)}
            payload[const.STORAGE] = node.get(const.CVG)
        return payload

    def _get_nodes(self, input_payload):
        """
        Get node details specific to cluster
        """
        Log.debug("Creating payload for nodes")
        nodes = input_payload.get(const.NODE)
        res = []
        for node_id in nodes.keys():
            res.append(self._create_node_payload(node_id, nodes.get(node_id)))
        return res

    def _get_durability(self, payload):
        dix = payload.get(const.DIX)
        sns = payload.get(const.SNS)
        res = {
            const.DATA: f"{dix.get(const.DATA)}+{dix.get(const.PARITY)}"\
                        f"+{dix.get(const.SPARE)}",
            const.METADATA: f"{sns.get(const.DATA)}+{sns.get(const.PARITY)}"\
                        f"+{sns.get(const.SPARE)}"
        }
        return res

    def _get_storage_set(self, payload):
        """
        Get storage_set details.
        """
        Log.debug("Creating payload for storage_sets")
        response = [{const.ID:storage_set[const.NAME], const.DURABILITY:\
            self._get_durability(storage_set[const.DURABILITY])} \
            for storage_set in payload]
        return response

    def _get_certificate_details(self, input_payload):
        """
        Get Certificate details
        """
        #TODO: Add device certificate/domain certificate once available.
        Log.debug("Creating payload for certificates")
        path = input_payload.get(const.CORTX).get(const.COMMON).get(const.SECURITY)\
            .get(const.SSL_CERTIFICATE)
        cert_details = SSLCertificate(path).get_certificate_details()
        cert_details = cert_details.get(const.CERT_DETAILS)
        cert_details[const.NAME] = Path(path).name
        cert_details[const.TYPE] = "SSL Certificate"
        return [cert_details]

    def _create_resource_payload(self, input_payload):
        """
        Generate payload for cluster with required attributes.
        """
        Log.debug("Creating payload for resources")
        cluster = input_payload[const.CLUSTER]
        payload = dict()
        payload[const.CLUSTER_ID] = cluster.get(const.ID)
        payload[const.VERSION] = input_payload.get(const.CORTX).\
                    get(const.COMMON).get(const.RELEASE).get(const.VERSION)
        payload[const.NODES] = self._get_nodes(input_payload)
        payload[const.STORAGE_SETS] = self._get_storage_set(cluster[const.STORAGE_SET])
        payload[const.CERTIFICATES] = self._get_certificate_details(input_payload)
        return payload

    def _convert(self, input_payload):
        """
        Convert topology payload schema to specific format.
        """
        coverted_payload = self._create_resource_payload(input_payload)
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
            Log.warn(f"index {const.TOPOLOGY_DICT_INDEX} is already loaded")
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
        try:
            orignal_payload = self._get_topology()
            payload  = self._convert(orignal_payload)
        except CsmNotFoundError as e:
            Log.error(f'Error in fetching certificate information: {e}')
            raise CsmInternalError("Unable to fetch topology information.")
        except ConfError as e:
            Log.error(f'Unable to fetch topology information: {e}')
            raise CsmInternalError("Unable to fetch topology information.")
        except Exception as e:
            Log.error(f'Unable to fetch topology information: {e}')
            raise CsmInternalError("Unable to fetch topology information.")
        return payload

class TopologyFactory:
    "Factory Class to get topology"
    def get_instance(config):
        "A method to get a instance of specific topology"
        topology = {
                const.CORTX : CortxTopology(config.get(const.URL))
        }
        obj_topology = topology[config.get(const.NAME).lower()]
        return obj_topology
