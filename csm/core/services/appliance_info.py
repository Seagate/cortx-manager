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

from csm.common.services import ApplicationService
from cortx.utils.appliance_info.appliance import ApplianceInfo
from cortx.utils.conf_store.conf_store import Conf
from csm.core.blogic import const

class ApplianceInfoService(ApplicationService):
    """
    Service for acessing appliance information
    """

    def __init__(self):
        self._appliance_obj = ApplianceInfo()

    async def get_appliance_info(self):
        """
        Loads the appliance info into memory and returns to the calling function.
        Currently the appliance info file contains only serail number and too
        not in a key value or dict format. It is just plain simple text.
        So, currenlty returning serial number only. In future when the appliance
        info file converts to key value then we will change the below code
        to send the complete dict instead of serial number.
        """
        ret_dict = {}
        self._appliance_obj.load()
        ret_dict["serial_number"] = self._appliance_obj.get().strip()
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, "PROVISIONER>cluster_id")
        ret_dict["cluster_id"] = cluster_id
        return {"appliance_info": [ret_dict]}
