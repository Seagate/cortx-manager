# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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

from csm.common.services import ApplicationService
from csm.core.services.rgw.s3.utils import CsmRgwConfigurationFactory

class RgwUsersService(ApplicationService):

    def __init__(self, plugin):
        self._rgw_plugin = plugin
        self._rgw_connection_config = CsmRgwConfigurationFactory.get_rgw_connection_config()
    
    async def create_user(self, **user_body):
        # To Do: confirm the function name of the plugin ???
        plugin_response = self._rgw_plugin.process_request(**user_body)
        return plugin_response
