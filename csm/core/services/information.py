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
from cortx.utils.schema.release import Release
from csm.common.services import ApplicationService

class InformationService(ApplicationService):
    """Information service class."""

    @Log.trace_method(Log.DEBUG)
    async def get_cortx_information(self, authorized=True, resource=None):
        """
        Method to fetch the cortx information

        :param **request_body: Request body kwargs
        """
        Log.debug(f"Request body: {resource}")
        # Call Utils API to get information
        response = {
            "authorized" : authorized
        }
        return response

