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
from cortx.utils.kv_store.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.utility import Utility
from cortx.utils.validator.error import VError

class Init(Setup):
    """Perform init operation for csm_setup."""

    def __init__(self):
        """Csm_setup init operation initialization."""
        super(Init, self).__init__()

    async def execute(self, command):
        """
        Execute csm_setup init operation.

        :param command:
        :return:
        """
        try:
            conf = command.options.get(const.CONFIG_URL)
            Utility.load_csm_config_indices(conf)
            Setup.setup_logs_init()
            Log.info("Init: Initiating Init phase.")
        except (KvError, VError) as e:
            Log.error(f"Init: Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        services = command.options.get("services")
        if ',' in services:
            services = services.split(",")
        elif 'all' in services:
            services = ["agent"]
        else:
            services=[services]
        if "agent" not in services:
            return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
        Log.info("Init: Successfully passed Init phase.")
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
