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


import crypt
import os
from cortx.utils.log import Log
from cortx.utils.conf_store import Conf
from cortx.utils.security.certificate import Certificate
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_pkg import PkgV
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.payload import Text
from cortx.utils.service.service_handler import Service
from cortx.utils.errors import SSLCertificateError

class PostInstall(Setup):
    """
    Perform post-install for csm
        : Configure csm user
        : Add Permission for csm user
    Post install is used after just all rpms are install but
    no service are started
    """

    def __init__(self):
        """Instiatiate Post Install Class."""
        Log.info("Executing Post Installation for CSM.")
        super(PostInstall, self).__init__()

    async def execute(self, command):
        """
        Execute all the Methods Required for Post Install Steps of CSM Rpm's.
        :param command: Command Class Object :type: class
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(
                const.CONFIG_URL))
            self.load_csm_config_indices()
            self._copy_base_configs()

        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")
        services = command.options.get("services")
        if ',' in services:
            services = services.split(",")
        elif 'all' in services:
            services = ["agent"]
        else:
            services=[services]
        if not "agent" in services:
            return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
        self._prepare_and_validate_confstore_keys()
        self.set_ssl_certificate()
        self.set_logpath()
        self.create()
        self.set_cluster_id()
        self.set_node_id()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
                const.KEY_SERVER_NODE_INFO: f"{const.NODE}>{self.machine_id}",
                const.KEY_SSL_CERTIFICATE:f"{const.SSL_CERTIFICATE_KEY}",
                const.KEY_LOGPATH:f"{const.CSM_LOG_PATH_KEY}",
                const.STORAGE_SET_NODES:f"{const.STORAGE_SET_NODES}"
                })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def set_ssl_certificate(self):
        ssl_certificate_path = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_SSL_CERTIFICATE])
        csm_protocol, csm_host, csm_port = self._parse_endpoints(
            Conf.get(const.CONSUMER_INDEX, const.CSM_AGENT_ENDPOINTS_KEY))
        if csm_protocol == 'https' and not os.path.exists(ssl_certificate_path):
            Log.warn(f"HTTPS enabled but SSL certificate not found at: {ssl_certificate_path}.\
                    Generating self signed ssl certificate")
            try:
                ssl_cert_configs = const.SSL_CERT_CONFIGS
                ssl_cert_obj = Certificate.init('ssl')
                ssl_cert_obj.generate(cert_path = ssl_certificate_path, dns_list = const.DNS_LIST,
                                            **ssl_cert_configs)
            except SSLCertificateError as e:
                Log.error(f"Failed to generate self signed ssl certificate: {e}")
                raise CsmSetupError("Failed to generate self signed ssl certificate")
            Log.info(f"Self signed ssl certificate generated and saved at: {ssl_certificate_path}")
        Conf.set(const.CSM_GLOBAL_INDEX, const.SSL_CERTIFICATE_PATH, ssl_certificate_path)
        Conf.set(const.CSM_GLOBAL_INDEX, const.PRIVATE_KEY_PATH_CONF, ssl_certificate_path)
        Log.info(f"Setting ssl certificate path: {ssl_certificate_path}")

    def set_logpath(self):
        log_path = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_LOGPATH])
        Conf.set(const.CSM_GLOBAL_INDEX, const.LOG_PATH, f"{log_path}/csm")
        Log.info(f"Setting log path: {log_path}")

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        Conf.save(const.CSM_GLOBAL_INDEX)

    def set_cluster_id(self):
        """
        This Function sets cluster_id in csm configuration.
        :return:
        """
        clusterid = Conf.get(const.CONSUMER_INDEX, const.CLUSTERID_KEY)
        Log.info(f"Setting cluster id:{clusterid}")
        Conf.set(const.CSM_GLOBAL_INDEX, const.KEY_CLUSTERID, clusterid)

    def set_node_id(self):
        """
        This Function Sets node id's for each storage set in csm configuration..
        :return:
        """
        node_ids = []
        Log.info("Fetching node ids from each storage set.")
        num_storage_sets = Conf.get(const.CONSUMER_INDEX, const.NUM_STORAGE_SET)
        for index in range(num_storage_sets):
            node_ids =  node_ids + Conf.get(const.CONSUMER_INDEX,
                                            f'cluster>storage_set[{index}]>nodes')
        Log.info("Setting node id.")
        Conf.set(const.CSM_GLOBAL_INDEX, const.NUM_NODE_ID, str(len(node_ids)))
        for index, node_id in enumerate(node_ids):
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.KEY_NODE_ID}[{index}]", str(node_id))