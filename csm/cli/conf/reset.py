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
from csm.core.providers.providers import Response
from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.common.errors import CSM_OPERATION_SUCESSFUL


class Reset(Setup):
    """
    Reset CORTX CLI configuration
    """

    def __init__(self):
        super(Reset, self).__init__()

    async def execute(self, command):
        """
        :param command:
        :return:
        """
        Log.info("Executing Reset for CORTX CLI Setup")
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CLI_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")
        self.reset_logs()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def reset_logs():
        '''
        Truncate size of cortxcli.log file to 0
        '''
        Log.info("Reseting log files")
        _file = os.path.join(Conf.get(const.CSM_GLOBAL_INDEX, 'Log>log_path'),
                                        "cortxcli.log")
        Setup._run_cmd(f"truncate -s 0 {_file}")
