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

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log
from cortx.utils.validator.v_consul import ConsulV
from cortx.utils.validator.error import VError
from csm.common.services import ApplicationService
from csm.core.blogic import const
import random

class SystemStatusService(ApplicationService):
    """
    Provides system status services
    """

    def __init__(self):
        super(SystemStatusService, self).__init__()
        self._action_map = {const.SYSTEM_STATUS_CONSUL: self._get_consul_status}

    async def check_status(self, resources):
        """
        Validate status of resource
        :param resources: list of resources.
        :return:
        """

        resp = dict()
        resp[const.SYSTEM_STATUS_SUCCESS] = True
        for each_resource in resources:
            Log.debug(f"Checking access for resource: {each_resource}")
            try:
                ret = await self._action_map.get(each_resource)()
                resp[each_resource] = ret
            except VError as ex:
                Log.error(f"Status check failed for {each_resource} exception : {ex}")
                resp[each_resource] = f"{ex.desc}"
                resp[const.SYSTEM_STATUS_SUCCESS] = False
        return resp

    async def _get_consul_status(self) -> str:
        """
        Return status of consul
        """
        Log.info("Getting consul status")
        # get host and port of consul database from conf
        hosts = Conf.get(const.DATABASE_INDEX, 'databases>consul_db>config>hosts')
        host = random.choice(hosts)
        port = Conf.get(const.DATABASE_INDEX, 'databases>consul_db>config>port')
        # Validation throws exception on failure
        ConsulV().validate('service', [host, port])
        return const.SYSTEM_STATUS_SUCCESS
