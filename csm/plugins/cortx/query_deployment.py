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
    cortx topology.
    """
    def __init__(self):
        """
        Initialize query deployment plugin
        """
        # set valid resources along with their attributes.
        self.valid_resources = {'cluster':['id', 'version', 'nodes', 'storage_set', 'certificate']}
        self.output = {
    'cortx': {
        'common': {
            'release': {
                'name': 'CORTX',
                'version': '2.0.0-5072'
            }
        }
    },
    'cluster': [
        {
        'id': '0007ec45379e36d9fa089a3d615c32a3',
        'name': 'cortx-cluster',
        'security': {
                'device_certificate': '/etc/cortx/solution/ssl/stx.pem',
                'domain_certificate': '/etc/cortx/solution/ssl/stx.pem',
                'ssl_certificate': '/etc/cortx/solution/ssl/s3.seagate.com.pem'
            },
        'storage_set_count': 1,
        'storage_set': [{
            'name': 'storage-set-1',
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
            }
            }]
    },
    {
        'id': '0007ec45379e36d9fa089a3d615c32a31',
        'name': 'cortx-cluster1',
        'security': {
                'device_certificate': '/etc/cortx/solution/ssl/stx.pem1',
                'domain_certificate': '/etc/cortx/solution/ssl/stx.pem1',
                'ssl_certificate': '/etc/cortx/solution/ssl/s3.seagate.com.pem'
            },
        'storage_set_count': 11,
        'storage_set': [{
            'name': 'storage-set-11',
            'durability': {
                'dix': {
                    'data': '11',
                    'parity': '0',
                    'spare': '0'
                },
                'sns': {
                    'data': '11',
                    'parity': '0',
                    'spare': '0'
                }
            }
            }]
    }],
    'nodes': [{
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'data1-node2',
            'name': 'data1-node2',
            'node_id': 'bbb340f79047df9bb52fa460615c32a5',
            'storage_set': 'storage-set-1',
            'type': 'data_node/1',
            'version': '2.0.0-84',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'motr',
                    'version': '2.0.0-5060',
                    'services': ['io']
                }, {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                }
            ],
            'cvg': [{
                'devices': {
                    'data': ['/dev/sdc', '/dev/sdd'],
                    'metadata': ['/dev/sdb'],
                    'log': ['/dev/sdh']
                },
                'name': 'cvg-01',
                'type': 'ios'
            }]
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'data2-node2',
            'name': 'data2-node2',
            'node_id': 'bba340f79047df9bb52fa460615c32a5',
            'storage_set': 'storage-set-1',
            'type': 'data_node/2',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'motr',
                    'version': '2.0.0-5060',
                    'services': ['io']
                }, {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                }
            ],
            'cvg': [{
                'devices': {
                    'data': ['/dev/sdf', '/dev/sdg'],
                    'metadata': ['/dev/sde'],
                    'log': ['/dev/sdi']
                },
                'name': 'cvg-02',
                'type': 'ios'
            }],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'ha-node',
            'name': 'ha-node',
            'node_id': '1115f539f4f770e2a3fe9e2e615c32a8',
            'storage_set': 'storage-set-1',
            'type': 'ha_node',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'ha',
                    'version': '2.0.0-5070'
                }
            ],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'data1-node3',
            'name': 'data1-node3',
            'node_id': 'ccc8700fe6797ed532e311b0615c32a7',
            'storage_set': 'storage-set-1',
            'type': 'data_node/1',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'motr',
                    'version': '2.0.0-5060',
                    'services': ['io']
                }, {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                }
            ],
            'cvg': [{
                'devices': {
                    'data': ['/dev/sdc', '/dev/sdd'],
                    'metadata': ['/dev/sdb'],
                    'log': ['/dev/sdh']
                },
                'name': 'cvg-01',
                'type': 'ios'
            }],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'ssc-vm-rhev4-2905.colo.seagate.com',
            'name': 'control-node',
            'node_id': '8efd697708a8f7e428d3fd520c180795',
            'storage_set': 'storage-set-1',
            'type': 'control_node',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'csm',
                    'services': ['agent'],
                    'version': '2.0.0-5072'
                }
            ],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'server-node3',
            'name': 'server-node3',
            'node_id': 'fff8700fe6797ed532e311b0615c32a7',
            'storage_set': 'storage-set-1',
            'type': 'server_node',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                },
                {
                    'name': 'rgw',
                    'version': '2.0.0-5073',
                    'services': ['rgw_s3']
                }
            ],
        },
        {
            'hostname': 'server-node2',
            'name': 'server-node2',
            'node_id': 'eee340f79047df9bb52fa460615c32a5',
            'storage_set': 'storage-set-1',
            'type': 'server_node',
            'version': '2.0.0-846',
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'hare'
                }, {
                    'name': 'rgw',
                    'version': '2.0.0-5073',
                    'services': ['rgw_s3']
                }
            ],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'data1-node1',
            'name': 'data1-node1',
            'node_id': 'aaa120a9e051d103c164f605615c32a4',
            'storage_set': 'storage-set-1',
            'type': 'data_node/1',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'motr',
                    'version': '2.0.0-5060',
                    'services': ['io']
                }, {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                }
            ],
            'cvg': [{
                'devices': {
                    'data': ['/dev/sdc', '/dev/sdd'],
                    'metadata': ['/dev/sdb'],
                    'log': ['/dev/sdh']
                },
                'name': 'cvg-01',
                'type': 'ios'
            }],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'server-node1',
            'name': 'server-node1',
            'node_id': 'ddd120a9e051d103c164f605615c32a4',
            'storage_set': 'storage-set-1',
            'type': 'server_node',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                },
                {
                    'name': 'rgw',
                    'version': '2.0.0-5073',
                    'services': ['rgw_s3']
                }
            ],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'data2-node3',
            'name': 'data2-node3',
            'node_id': 'cca8700fe6797ed532e311b0615c32a7',
            'storage_set': 'storage-set-1',
            'type': 'data_node/2',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'motr',
                    'version': '2.0.0-5060',
                    'services': ['io']
                }, {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                }
            ],
            'cvg': [{
                'devices': {
                    'data': ['/dev/sdf', '/dev/sdg'],
                    'metadata': ['/dev/sde'],
                    'log': ['/dev/sdi']
                },
                'name': 'cvg-02',
                'type': 'ios'
            }],
        },
        {
            'cluster_id': '0007ec45379e36d9fa089a3d615c32a3',
            'hostname': 'data2-node1',
            'name': 'data2-node1',
            'node_id': 'eee120a9e051d103c164f605615c32a4',
            'storage_set': 'storage-set-1',
            'type': 'data_node/2',
            'version': '2.0.0-846',
            'components': [{
                    'name': 'utils',
                    'version': '2.0.0-5058'
                },
                {
                    'name': 'motr',
                    'version': '2.0.0-5060',
                    'services': ['io']
                }, {
                    'name': 'hare',
                    'version': '2.0.0-5072'
                }
            ],
            'cvg': [{
                'devices': {
                    'data': ['/dev/sdf', '/dev/sdg'],
                    'metadata': ['/dev/sde'],
                    'log': ['/dev/sdi']
                },
                'name': 'cvg-02',
                'type': 'ios'
            }],
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
        payload = {}
        payload[const.ID] = node[const.ARG_NODE_ID]
        payload[const.VERSION] = node[const.VERSION]
        payload[const.TYPE] = node[const.TYPE]
        payload[const.COMPONENTS] = node[const.COMPONENTS]
        if node.get(const.CVG):
            payload[const.CVG] = node.get(const.CVG)
        return payload

    def _get_nodes(self, attribute, input_payload, cluster_id):
        """
        Get node details specific to cluster
        """
        nodes = input_payload[const.NODES]
        res = []
        for node in nodes:
            if node[const.CLUSTER_ID] == cluster_id:
                res.append(self._create_node_payload(node))
        return res

    def _create_cluster_payload(self, resource, valid_attributes, input_payload):
        """
        Generate payload for clusters.
        """
        res  = []
        total_clusters = input_payload[resource]
        for cluster in total_clusters:
            partial_payload = {}
            for attribute in valid_attributes:
                if attribute == const.ID or attribute == const.STORAGE_SET:
                    partial_payload[attribute] = cluster[attribute]
                elif attribute == const.NODES:
                    cluster_id = cluster[const.ID]
                    partial_payload[attribute] = self._get_nodes(attribute, input_payload, cluster_id)
                elif attribute == const.CERTIFICATE:
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
        Get topology of cortx deployment
        """
        # 1. Call utils interface
        # Uncomment after integration
        # topology = QueryDeployment._get_cortx_topology({""})
        topology = self.output
        self.validate_input(topology)
        res = self.convert_schema(topology)
        return res
