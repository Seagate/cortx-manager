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
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError


class Init(Setup):
    """
    Init CORTX CLI
    """

    def __init__(self):
        super(Init, self).__init__()

    async def execute(self, command):
        """
        Execute CORTX CLI setup Init Command
        :param command: Command Object For CLI. :type: Command
        :return: 0 on success, RC != 0 otherwise.
        """

        Log.info("Executing Init for CORTX CLI")
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CLI_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        self._prepare_and_validate_confstore_keys()
        self._config_user_permission()

        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}"
        })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX,
                                keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def _config_user_permission(self):
        """
        Set User Permission
        """
        self._user = Conf.get(const.CONSUMER_INDEX,
                                    self.conf_store_keys.get(const.KEY_CSM_USER))
        Log.info("Set User Permission")
        log_path = Conf.get(const.CORTXCLI_GLOBAL_INDEX, "Log>log_path")
        os.makedirs(log_path, exist_ok=True)
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {log_path}")
