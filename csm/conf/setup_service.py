# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.v_pkg import PkgV
from csm.core.providers.providers import Response
from csm.core.blogic import const
from cortx.utils.validator.error import VError
from csm.common.errors import CSM_OPERATION_SUCESSFUL, CsmSetupError
from cortx.utils.log import Log
from csm.conf.setup import Setup

class Setup_Service(Setup):
    """
    Perform Setup_Service operations for csm
    Executes setup for all csm services i.e. agent, web and cli as per args
    """
    def __init__(self):
        super(Setup_Service, self).__init__()

    async def execute(self, command):
        Log.info("Perform Setup_Service for csm services")
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(
                const.CONFIG_URL))
            self.config_path = self._set_csm_conf_path()
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        service_name = command.options.get("service")
        config_url = command.options.get("config_url")
        if service_name in ["all", "csm_agent"]:
            #Execute only csm-setup
            for each_phase in ["post_install", "prepare", "config", "init"]:
                Log.info(f"Executing Csm-Setup -> {each_phase} phase")
                Setup._run_cmd(f"csm_setup {each_phase} --config {config_url}")
        self.execute_web_and_cli(command.options.get("config_url"),
                                    service_name)

        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
