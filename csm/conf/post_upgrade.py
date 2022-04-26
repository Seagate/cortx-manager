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
from csm.conf.post_install import PostInstall
from csm.conf.prepare import Prepare
from csm.conf.configure import Configure
from csm.conf.init import Init
from csm.conf.setup import Setup
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL


class PostUpgrade(PostInstall, Prepare, Configure, Init, Setup):
    """
    Perform post-upgrade for regenerating the coonfigurations after
    upgrade is done.
    """

    def __init__(self):
        """Instiatiate Post Install Class."""
        super(PostUpgrade, self).__init__()
        Log.info("Executing Post Upgrade for CSM.")

    async def execute(self, command):
        """
        Execute csm_setup post upgrade operation.

        :param command:
        :return:
        """ 
        # TODO: Implement post upgrade logic
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
