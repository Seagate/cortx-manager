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
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.conf.setup import Setup
from csm.common.errors import CSM_OPERATION_SUCESSFUL


class Test(Setup):
    """
    Test CORTX CLI

    Run tests to ensure CORTX CLI is set up properly.
    """

    def __init__(self):
        """Initialize CORTX CLI tests."""
        super(Test, self).__init__()

    async def execute(self, command):
        """
        Execute CORTX CLI setup Test Command

        :param command: Command Object For CLI. :type: Command
        :return: 0 on success, RC != 0 otherwise.
        """

        Log.info("Executing Test for CORTX CLI")
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
