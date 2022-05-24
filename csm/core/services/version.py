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
from csm.core.blogic import const
from csm.common.services import ApplicationService

class VersionValidationService(ApplicationService):
    """Version Comptibility Validation service class."""

    @Log.trace_method(Log.DEBUG)
    async def is_version_compatible(self, **request_body):
        """
        Method to check whether new requirements are compatible with deployed version

        :param **request_body: Request body kwargs
        """
        Log.debug(f"Request body: {request_body}")
        response = {
            "node_id": request_body.get(const.ARG_RESOURCE_ID),
            "compatible": True,
            "reason": "Current version is compatible"
        }
        return response

