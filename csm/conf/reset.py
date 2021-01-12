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
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL

class Reset(Setup):
    """
    Reset csm configuraion
    Soft: Soft Reset is used to restrat service with log cleanup
        - Cleanup all log
        - Reset conf
        - Restart service
    Hard: Hard reset is used to remove all configuration used by csm
        - Stop service
        - Cleanup all log
        - Delete all Dir created by csm
        - Cleanup Job
        - Disable csm service
        - Delete csm user
    """
    def __init__(self):
        super(Reset, self).__init__()
        Log.info("Triggering csm_setup reset")

    def execute(self, command):
        """
        :param command:
        :return:
        """
        try:
            self.Config.reset()
            self.ConfigServer.restart()
        except Exception as e:
            import traceback
            Log.error(f"csm_setup reset failed. Error: {e} - {str(traceback.print_exc())}")
            raise CsmSetupError(f"csm_setup reset failed. Error: {e} - {str(traceback.print_exc())}")
        return Response(output=":PASS", rc=CSM_OPERATION_SUCESSFUL)

