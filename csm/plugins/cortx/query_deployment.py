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
#from cortx.utils.query_deployment import QueryDeployment


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
        self.output = {
	'cortx': {
		'common': {
			'release': {
				'name': 'CORTX',
				'version': '2.0.0-7440'
			}
		}
	},
	'clusters': [{
		'id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'security': {
			'device_certificate': '/etc/cortx/solution/ssl/stx.pem',
			'domain_certificate': '/etc/cortx/solution/ssl/stx.pem',
			'ssl_certificate': '/etc/cortx/solution/ssl/s3.seagate.com.pem'
		},
		'storage_set': [{
			'durability': {
				'dix': {
					'data': '1',
					'parity': '0',
					'spare': '0'
				},
				'sns': {
					'data': '1',
					'parity': '0',
					'spare': '0'
				}
			},
			'name': 'storage-set-1'
		}]
	}],
	'nodes': [{
		'machine_id': '3b404b96fc01319b5edb2e84e323595a',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}, {
			'name': 'rgw',
			'services': ['rgw_s3'],
			'version': '2.0.0-7440'
		}],
		'hostname': 'cortx-server-1.cortx-server-headless.cortx.svc.cluster.local',
		'name': 'cortx-server-1',
		'node_id': 'cortx-server-1.cortx-server-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606892',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'server_node'
	}, {
		'machine_id': '6ac2b08cfe659acf910fed4d11b7df53',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'motr',
			'services': ['io'],
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}],
		'cvg': [{
			'devices': {
				'data': ['/dev/sdd', '/dev/sde'],
				'metadata': ['/dev/sdc']
			},
			'name': 'cvg-01',
			'type': 'ios'
		}],
		'hostname': 'cortx-data-g0-2.cortx-data-headless.cortx.svc.cluster.local',
		'name': 'cortx-data-g0-2',
		'node_group': 'ssc-vm-g2-rhev4-3260.colo.seagate.com',
		'node_id': 'cortx-data-g0-2.cortx-data-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606856',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'data_node/0'
	}, {
		'machine_id': '7ba8990a85d38508ca9bac4ff516d3ea',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'motr',
			'services': ['io'],
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}],
		'cvg': [{
			'devices': {
				'data': ['/dev/sdd', '/dev/sde'],
				'metadata': ['/dev/sdc']
			},
			'name': 'cvg-01',
			'type': 'ios'
		}],
		'hostname': 'cortx-data-g0-0.cortx-data-headless.cortx.svc.cluster.local',
		'name': 'cortx-data-g0-0',
		'node_group': 'ssc-vm-g2-rhev4-3262.colo.seagate.com',
		'node_id': 'cortx-data-g0-0.cortx-data-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606855',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'data_node/0'
	}, {
		'machine_id': '7d9ee991ae6ce628a0e10294bdebaa6b',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'ha',
			'version': '2.0.0-7440'
		}],
		'hostname': 'cortx-ha-headless',
		'name': 'cortx-ha',
		'node_id': 'cortx-ha-headless',
		'deployment_time': '1659606866',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'ha_node'
	}, {
		'machine_id': 'aa378e768a2ba5291d786b3dc48d5650',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'motr',
			'services': ['io'],
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}],
		'cvg': [{
			'devices': {
				'data': ['/dev/sdg', '/dev/sdh'],
				'metadata': ['/dev/sdf']
			},
			'name': 'cvg-02',
			'type': 'ios'
		}],
		'hostname': 'cortx-data-g1-0.cortx-data-headless.cortx.svc.cluster.local',
		'name': 'cortx-data-g1-0',
		'node_group': 'ssc-vm-g2-rhev4-3262.colo.seagate.com',
		'node_id': 'cortx-data-g1-0.cortx-data-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606852',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'data_node/1'
	}, {
		'machine_id': 'ac2f9656e38a92990522025e1f3ccaef',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}, {
			'name': 'rgw',
			'services': ['rgw_s3'],
			'version': '2.0.0-7440'
		}],
		'hostname': 'cortx-server-0.cortx-server-headless.cortx.svc.cluster.local',
		'name': 'cortx-server-0',
		'node_id': 'cortx-server-0.cortx-server-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606889',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'server_node'
	}, {
		'machine_id': 'cd1e4c61d297a784245dd88106262cd3',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'motr',
			'services': ['io'],
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}],
		'cvg': [{
			'devices': {
				'data': ['/dev/sdd', '/dev/sde'],
				'metadata': ['/dev/sdc']
			},
			'name': 'cvg-01',
			'type': 'ios'
		}],
		'hostname': 'cortx-data-g0-1.cortx-data-headless.cortx.svc.cluster.local',
		'name': 'cortx-data-g0-1',
		'node_group': 'ssc-vm-g2-rhev4-3261.colo.seagate.com',
		'node_id': 'cortx-data-g0-1.cortx-data-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606854',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'data_node/0'
	}, {
		'machine_id': 'd62dc0d2c3ee12aee9b946379519133a',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}, {
			'name': 'rgw',
			'services': ['rgw_s3'],
			'version': '2.0.0-7440'
		}],
		'hostname': 'cortx-server-2.cortx-server-headless.cortx.svc.cluster.local',
		'name': 'cortx-server-2',
		'node_id': 'cortx-server-2.cortx-server-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606892',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'server_node'
	}, {
		'machine_id': 'ecabccb4bced858e282f568d6bf04558',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'csm',
			'services': ['agent'],
			'version': '2.0.0-7440'
		}],
		'hostname': 'cortx-control',
		'name': 'cortx-control',
		'node_id': 'cortx-control',
		'deployment_time': '1659606820',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'control_node'
	}, {
		'machine_id': 'f488442b875fe8c4328e148f8aca7aa7',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'motr',
			'services': ['io'],
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}],
		'cvg': [{
			'devices': {
				'data': ['/dev/sdg', '/dev/sdh'],
				'metadata': ['/dev/sdf']
			},
			'name': 'cvg-02',
			'type': 'ios'
		}],
		'hostname': 'cortx-data-g1-2.cortx-data-headless.cortx.svc.cluster.local',
		'name': 'cortx-data-g1-2',
		'node_group': 'ssc-vm-g2-rhev4-3260.colo.seagate.com',
		'node_id': 'cortx-data-g1-2.cortx-data-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606856',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'data_node/1'
	}, {
		'machine_id': 'fae544140e673b0f2a0d26cb2011516a',
		'cluster_id': '752a4fa7-45e9-4f61-a7e0-e204fd439c0e',
		'components': [{
			'name': 'utils',
			'version': '2.0.0-7440'
		}, {
			'name': 'motr',
			'services': ['io'],
			'version': '2.0.0-7440'
		}, {
			'name': 'hare',
			'version': '2.0.0-7440'
		}],
		'cvg': [{
			'devices': {
				'data': ['/dev/sdg', '/dev/sdh'],
				'metadata': ['/dev/sdf']
			},
			'name': 'cvg-02',
			'type': 'ios'
		}],
		'hostname': 'cortx-data-g1-1.cortx-data-headless.cortx.svc.cluster.local',
		'name': 'cortx-data-g1-1',
		'node_group': 'ssc-vm-g2-rhev4-3261.colo.seagate.com',
		'node_id': 'cortx-data-g1-1.cortx-data-headless.cortx.svc.cluster.local',
		'deployment_time': '1659606856',
		'version': '2.0.0-7440',
		'storage_set': 'storage-set-1',
		'type': 'data_node/1'
	}]
}

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
        cert_details = cert_details[const.CERT_DETAILS]
        cert_details[const.PATH] = path
        cert_details[const.TYPE] = "SSL Certificate"
        return [cert_details]

    def _create_node_payload(self, node):
        """
        Create payload for given node
        """
        # TODO: Use get method
        payload = {}
        payload[const.ID] = node[const.MACHINE_ID]
        payload[const.HOSTNAME] = node[const.HOSTNAME]
        payload[const.VERSION] = node[const.VERSION]
        payload[const.DEPLOYMENT_TIME] = node[const.DEPLOYMENT_TIME]
        payload[const.TYPE] = node[const.TYPE]
        payload[const.COMPONENTS] = node[const.COMPONENTS]
        if node.get(const.CVG):
            payload[const.CVG] = node.get(const.CVG)
        return payload

    def _get_nodes(self, input_payload, cluster_id):
        """
        Get node details specific to cluster
        """
        nodes = input_payload[const.NODES]
        res = []
        for node in nodes:
            if node[const.CLUSTER_ID] == cluster_id:
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
        res  = []
        total_clusters = input_payload[resource]
        for cluster in total_clusters:
            partial_payload = {}
            for attribute in valid_attributes:
                if attribute == const.ID:
                    partial_payload[attribute] = cluster.get(attribute) if cluster.get(attribute) \
						else cluster.get(const.CLUSTER)
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

    def get_topology(self):
        """
        Get topology of deployment
        """
        # TODO: Uncomment following call after integration
        # consul://cortx-consul-server:8500/conf
        # topology = QueryDeployment.get_cortx_topology("consul://cortx-consul-server:8500/conf")
        # use try
        #topology = QueryDeployment.get_cortx_topology("consul://cortx-consul-server:8500/conf")
        topology = self.output
        res = self.convert_schema(topology)
        self.validate_input(res)
        return res
