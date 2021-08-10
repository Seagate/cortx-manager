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
import traceback
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.log import Log
from cortx.utils.validator.v_elasticsearch import ElasticsearchV
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL


class Configure(Setup):
    """
    Configure CORTX CLI

    Config is used to move/update configuration files (one time configuration).
    """

    def __init__(self):
        super(Configure, self).__init__()
        Setup._copy_cli_skeleton_configs()

    async def execute(self, command):
        """
        Execute CORTX CLI setup Config Command

        :param command: Command Object For CLI. :type: Command
        :return: 0 on success, RC != 0 otherwise.
        """

        Log.info("Executing Config for CORTX CLI")
        try:
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CLI_CONF_URL)
            Conf.load(const.DATABASE_CLI_INDEX, const.DATABASE_CLI_CONF_URL)
        except KvError as e:
            err_msg = f"Failed to load the configuration: {e}"
            Log.error(err_msg)
            raise CsmSetupError(err_msg)
        except Exception as e:
            err_msg = (f"cli_setup config command failed. Error: "
                       f"{e} - {str(traceback.format_exc())}")
            Log.error(err_msg)
            raise CsmSetupError(err_msg)
        self._prepare_and_validate_confstore_keys()
        self._validate_es_service()
        self._configure_agent_details()
        self.cli_create()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SERVER_NODE_INFO:f"{const.SERVER_NODE_INFO}",
            const.KEY_SERVER_NODE_TYPE:f"{const.SERVER_NODE_INFO}>{const.TYPE}",
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}",
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}"
            })

        Setup._validate_conf_store_keys(const.CONSUMER_INDEX,
                                keylist = list(self.conf_store_keys.values()))

    def _validate_es_service(self):
        Log.info("Getting elasticsearch status")
        # get host and port of consul database from conf
        es_hosts = Conf.get(const.DATABASE_CLI_INDEX, 'databases>es_db>config>hosts')
        if not es_hosts: raise CsmSetupError("Elasticsearch host not available.")
        es_hosts.append(const.LOCALHOST)
        port = Conf.get(const.DATABASE_CLI_INDEX, 'databases>es_db>config>port')
        if not port: raise CsmSetupError("Elasticsearch port not available.")
        # Validation throws exception on failure
        for host in es_hosts:
            ElasticsearchV().validate('service', [host, port])

    def _configure_agent_details(self):
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        agent_host_key = f"{const.CLUSTER}>{cluster_id}>{const.NETWORK}>{const.MANAGEMENT}>agent_host"
        agent_port_key = f"{const.CLUSTER}>{cluster_id}>{const.NETWORK}>{const.MANAGEMENT}>agent_port"
        agent_protocol_key = f"{const.CLUSTER}>{cluster_id}>{const.NETWORK}>{const.MANAGEMENT}>agent_protocol"
        agent_host = Conf.get(const.CONSUMER_INDEX, agent_host_key, "127.0.0.1")
        agent_port = Conf.get(const.CONSUMER_INDEX, agent_port_key, "28101")
        agent_prototcol = Conf.get(const.CONSUMER_INDEX, agent_protocol_key, "http://")

        Log.info(f"Setting Csm agent host:{agent_host}, port:{agent_port}, protocol:{agent_prototcol}")
        Conf.set(const.CORTXCLI_GLOBAL_INDEX,'CORTXCLI>csm_agent_port', agent_port)
        Conf.set(const.CORTXCLI_GLOBAL_INDEX,'CORTXCLI>csm_agent_host', agent_host)
        Conf.set(const.CORTXCLI_GLOBAL_INDEX,'CORTXCLI>csm_agent_base_url', agent_prototcol)

    def cli_create(self):
        """
        Create the CortxCli configuration file on the required location.
        """
        if self._is_env_dev:
            Conf.set(const.CORTXCLI_GLOBAL_INDEX,
                     f"{const.DEPLOYMENT}>{const.MODE}", const.DEV)
        Conf.save(const.CORTXCLI_GLOBAL_INDEX)
        Conf.save(const.DATABASE_CLI_INDEX)