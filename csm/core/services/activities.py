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

import json

from csm.core.blogic import const
from csm.common.services import ApplicationService
from csm.common.errors import CsmInternalError, CsmNotFoundError

from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.activity_tracker.activity_store import Activity, ActivityEntry
from cortx.utils.activity_tracker.error import ActivityError


class ActivityService(ApplicationService):
    """Activity management service class."""

    def __init__(self):
        """
        Initializes Activity management service."""
        consul_host = Conf.get(const.DATABASE_INDEX,
                               f'{const.DB_CONSUL_CONFIG_HOST}[{0}]')
        consul_port = Conf.get(const.DATABASE_INDEX,
                               const.DB_CONSUL_CONFIG_PORT)
        store_path = "cortx/activity/"
        self._backend_url = f"consul://{consul_host}:{consul_port}/{store_path}"
        self.is_kv_store_initialzed: bool = False

    async def activity_init(self):
        if not self.is_kv_store_initialzed:
            Log.info("Activity tracker backend initialized.")
            Activity.init(self._backend_url)
            self.is_kv_store_initialzed = True

    @Log.trace_method(Log.DEBUG)
    async def create(self, **request_body):
        _name = request_body.get(const.NAME)
        try:
            await self.activity_init()
            activity: ActivityEntry = Activity.create(
                _name, 
                request_body.get(const.RESOURCE_PATH),
                request_body.get(const.DESCRIPTION))
            return json.loads(activity.payload.json)
        except ActivityError as ae:
            Log.error(f'Failed to create a new activity: {ae}')
            raise CsmInternalError(const.ACTIVITY_ERROR)

    @Log.trace_method(Log.DEBUG)
    async def get_by_id(self, id):
        try:
            await self.activity_init()
            activity: ActivityEntry = Activity.get(id)
            return json.loads(activity.payload.json)
        except ActivityError as ae:
            if "get(): invalid activity id" in str(ae):
                Log.error(f'Failed to fetch the activity. Activity with id= {id} does not exist: {ae}')
                raise CsmNotFoundError(f"Activity with id= {id} does not exist", const.ACTIVITY_NOT_FOUND)
            Log.error(f'Failed to fetch the activity by id= {id}: {ae}')
            raise CsmInternalError(const.ACTIVITY_ERROR)

    @Log.trace_method(Log.DEBUG)
    async def update_by_id(self, **request_body):
        _id = request_body.get(const.ID)
        try:
            await self.activity_init()
            activity: ActivityEntry = Activity.get(_id)
            Activity.update(activity, request_body.get(const.PROGRESS),
                                  request_body.get(const.STATUS_LITERAL), request_body.get(const.STATUS_DESC))
            return json.loads(activity.payload.json)
        except ActivityError as ae:
            if "get(): invalid activity id" in str(ae):
                Log.error(f'Failed to update the activity. Activity with id= {id} does not exist: {ae}')
                raise CsmNotFoundError(f"Activity does not exist: {_id}", const.ACTIVITY_NOT_FOUND)
            Log.error(f'Failed to update the activity by id= {id}: {ae}')
            raise CsmInternalError(const.ACTIVITY_ERROR)
