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
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError


class Cleanup(Setup):
    """
    Delete all the CLI generated files and folders
    """

    def __init__(self):
        super(Cleanup, self).__init__()
        Log.info("Triggering Cleanup for Cortxcli setup.")

    async def execute(self, command):
        """
        Execute CORTX CLI setup Cleanup Command
        :param command: Command Object For CLI. :type: Command
        :return: 0 on success, RC != 0 otherwise.
        """
        Log.info("Executing Cleanup for CORTX CLI Setup")
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CLI_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")
        if command.options.get("pre-factory"):
            # Placeholder for pre-factory cleanup.
            Log.info("Execute pre-factory cleanup for cli setup")
        self.files_directory_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)


    def files_directory_cleanup(self):
        '''
        Remove CLI config and log directory
        '''
        files_directory_list = [
            Conf.get(const.CORTXCLI_GLOBAL_INDEX, 'Log>log_path'),
            const.CORTXCLI_CONF_PATH
        ]
        for dir_path in files_directory_list:
            Log.info(f"Deleteing path :{dir_path}")
            Setup._run_cmd(f"rm -rf {dir_path}")
