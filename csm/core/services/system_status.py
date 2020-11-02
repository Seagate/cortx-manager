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

from csm.common.conf import Conf
from cortx.utils.log import Log
from cortx.utils.validator.v_consul import ConsulV
from cortx.utils.validator.v_network import NetworkV
from csm.common.conf import Conf
from csm.common.services import ApplicationService
from csm.core.blogic import const


class SystemStatusService(ApplicationService):
    """
    Provides system status services
    """

    def __init__(self, conf):
        super(SystemStatusService, self).__init__()
        self._conf = conf
        self._action_map = {const.SYSTEM_STATUS_CONSUL: self._get_consul_status,
            const.SYSTEM_STATUS_ELASTICSEARCH: self._get_elasticsearch_status}

    async def check_status(self, check_list):
        """
        Validate status of resource
        :param check_list: list of resources.
        :return:
        """

        resp = dict()
        resp['success'] = True
        Log.debug(f" action_map: {self._action_map}")
        Log.debug(f" check_list: {check_list}")
        for each_resource in check_list:
            Log.debug(f" each resource: {each_resource}")
            try:
                ret = await self._action_map.get(each_resource)()
                resp[each_resource] = ret
            except Exception as ex:
                Log.error(f"Status check failed for {each_resource} exception : {ex}")
                resp[each_resource] = "failed"
                resp['success'] = False
        return resp

    async def _get_consul_status(self) -> str:
        """
        Return status of consul
        """
        Log.info("Get consul status")


        # get host and port of consul database from conf
        host = "192.168.28.244"
        port = '8500'
        # Validation throws exception on failure 
        ConsulV().validate('service', [host, port])
        return "success"

    async def _get_elasticsearch_status(self) -> str:
        """
        Return status of consul
        """
        Log.info("Get consul status")
        # get host and port of consul database from conf
        host = "192.168.12.247"
        # Validation throws exception on failure 
        NetworkV().validate('connectivity', [host])
        return "success"
