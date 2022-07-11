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
from cortx.utils.log import Log
from cortx.utils.conf_store import Conf
from cortx.utils.security.certificate import Certificate
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.errors import SSLCertificateError
from csm.common.service_urls import ServiceUrls

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
        Execute csm_setup post install operation.

        :param command: Command Class Object :type: class
        :return:
        """
        try:
            Conf.load(const.CONSUMER_INDEX, command.options.get(
                const.CONFIG_URL))
            Setup.setup_logs_init()
            Log.info("Executing csm_setup: post_install phase.")
            Setup.load_csm_config_indices()
            Setup.copy_base_configs()
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
        PostInstall.set_logpath()
        self.create()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SSL_CERTIFICATE:f"{const.SSL_CERTIFICATE_KEY}"
            })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def set_ssl_certificate(self):
        ssl_certificate_path = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_SSL_CERTIFICATE])
        csm_protocol, *_ = ServiceUrls.parse_url(
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

    @staticmethod
    def set_logpath():
        log_path = Setup.get_csm_log_path()
        Conf.set(const.CSM_GLOBAL_INDEX, const.LOG_PATH, log_path)
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
