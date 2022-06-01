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

import ast
import os
from cortx.utils.log import Log
from csm.conf.setup import Setup, CsmSetupError
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.validator.error import VError


class Prepare(Setup):
    """Perform prepare operation for csm_setup."""

    def __init__(self):
        """Csm_setup prepare operation initialization."""
        super(Prepare, self).__init__()
        Log.info("Triggering csm_setup prepare")
        self._replacement_node_flag = os.environ.get(
            "REPLACEMENT_NODE") == "true"
        if self._replacement_node_flag:
            Log.info("REPLACEMENT_NODE flag is set")

    async def execute(self, command):
        """
        Execute csm_setup prepare operation.

        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Setup.load_csm_config_indices()
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
        self._set_secret_string_for_decryption()
        self._set_cluster_id()
        # TODO: set configurations of perf stats once keys are available in conf-store.
        # self._set_msgbus_perf_stat_info()
        Prepare._set_db_host_addr()
        self.create()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
                const.KEY_SERVER_NODE_INFO:f"{const.NODE}>{self.machine_id}",
                const.KEY_HOSTNAME:f"{const.NODE}>{self.machine_id}>{const.HOSTNAME}",
                const.KEY_CLUSTER_ID:const.CLUSTER_ID_KEY,
                const.CONSUL_ENDPOINTS_KEY:f"{const.CONSUL_ENDPOINTS_KEY}",
                const.CONSUL_SECRET_KEY:f"{const.CONSUL_SECRET_KEY}"
                # TODO: validate following keys once available in conf-store
                #const.METRICS_PERF_STATS_MSG_TYPE : const.METRICS_PERF_STATS_MSG_TYPE_KEY,
                #const.METRICS_PERF_STATS_RETENTION_SIZE:const.METRICS_PERF_STATS_RETENTION_SIZE_KEY
                })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def _set_secret_string_for_decryption(self):
        """
        This will be the root of csm secret key
        eg: for "cortx>software>csm>secret" root is "cortx".
        """
        Log.info("Set decryption keys for CSM and S3")
        Conf.set(const.CSM_GLOBAL_INDEX, const.KEY_DECRYPTION,
                    self.conf_store_keys[const.CONSUL_ENDPOINTS_KEY].split('>')[0])

    def _set_cluster_id(self):
        Log.info("Setting up cluster id")
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        if not cluster_id:
            raise CsmSetupError("Failed to fetch cluster id")
        Conf.set(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY, cluster_id)

    @staticmethod
    def _set_db_host_addr():
        """
        Sets database hosts address in CSM config.
        :return:
        """
        _, consul_host, consul_port, secret, _ = Setup.get_consul_config()
        consul_login = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ADMIN_KEY)
        consul_endpoint_len = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ENDPOINTS_LEN)
        endpoint_list = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ENDPOINTS_KEY)
        try:
            if consul_host and consul_port:
                Conf.set(const.DATABASE_INDEX,
                        f'{const.DB_CONSUL_CONFIG_HOST}[{0}]',
                        consul_host)
                Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_PORT, consul_port)
            Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_PASSWORD, secret)
            Conf.set(const.DATABASE_INDEX, const.DB_CONSUL_CONFIG_LOGIN, consul_login)
            Conf.set(const.CSM_GLOBAL_INDEX, const.CONSUL_ADMIN_KEY, consul_login)
            Conf.set(const.CSM_GLOBAL_INDEX, const.CONSUL_ENDPOINTS_LEN, consul_endpoint_len)
            Conf.set(const.CSM_GLOBAL_INDEX, const.CONSUL_SECRET_KEY, secret)
            for endpoint_count in range(consul_endpoint_len):
                Conf.set(const.CSM_GLOBAL_INDEX,
                        f'{const.CONSUL_ENDPOINTS_KEY}[{endpoint_count}]',
                        ast.literal_eval(f'{endpoint_list}[{endpoint_count}]'))
        except Exception as e:
            Log.error(f'Unable to set host address: {e}')
            raise CsmSetupError(f'Unable to set host address: {e}')

    def _set_msgbus_perf_stat_info(self):
        msg_type = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.METRICS_PERF_STATS_MSG_TYPE])
        retention_size = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.METRICS_PERF_STATS_RETENTION_SIZE])
        Log.info(f"Set message_type:{msg_type} and retention_size:{retention_size} for perf_stat")
        Conf.set(const.CSM_GLOBAL_INDEX, const.MSG_BUS_PERF_STAT_MSG_TYPE, msg_type)
        Conf.set(const.CSM_GLOBAL_INDEX, const.MSG_BUS_PERF_STAT_RETENTION_SIZE, retention_size)

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, const.CSM_DEPLOYMENT_MODE,
                     const.DEV)
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)
