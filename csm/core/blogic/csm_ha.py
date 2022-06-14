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

import os
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from csm.common.errors import CsmError
from csm.core.blogic import const
from csm.common.ha_framework import PcsResourceAgent

class CsmResourceAgent(PcsResourceAgent):
    """Provide initalization on csm resources."""

    def __init__(self, resources):
        """Csm resource agent init."""
        super(CsmResourceAgent, self).__init__(resources)
        self._resources = resources
        self._csm_index = const.CSM_GLOBAL_INDEX
        self._primary = Conf.get(const.CSM_GLOBAL_INDEX, "HA>primary")
        self._secondary = Conf.get(const.CSM_GLOBAL_INDEX, "HA>secondary")

    def init(self, force_flag):
        """Perform initalization for CSM resources"""
        try:
            Log.info("Starting configuring HA for CSM..")

            if force_flag:
                # if self.is_available():
                #     self._delete_resource()
                if os.path.exists(const.HA_INIT):
                    os.remove(const.HA_INIT)

            # Check if resource already configured
            # if self.is_available():
            #     if not os.path.exists(const.HA_INIT):
            #         open(const.HA_INIT, 'a').close()
            #     Log.info("Csm resources are already configured...")
            #     return True

            self._ra_init()

            for resource in self._resources:
                service = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES>" + resource + ">service")
                provider = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES>" + resource + ">provider")
                interval = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES>" + resource + ">interval")
                timeout = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES>" + resource + ">timeout")
                self._init_resource(resource, service, provider, interval, timeout)

            # TODO- check score for failback
            self._init_constraint("INFINITY")
            # self._execute_config()
            open(const.HA_INIT, 'a').close()
            Log.info("Successed: Configuring HA for CSM..")
            return True
        except CsmError as err:
            Log.exception("%s" %err)
            raise CsmError(-1, "Error: Unable to configure csm resources...")

    def failover(self):
        #TODO
        pass
