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

from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.log import Log
from csm.conf.setup import Setup

class PreUpgrade(Setup):
    """
    Perform preinstall operations for csm
    """
    def __init__(self):
        super(PreUpgrade, self).__init__()

    async def execute(self, command):
        Log.info("Perform preupgrade for csm_setup")
        # TODO: Implement preupgrade logic
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
