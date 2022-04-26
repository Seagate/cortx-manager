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

import datetime
from cortx.utils.data.db.db_provider import DataBaseProvider
from cortx.utils.data.access.filters import Compare
from cortx.utils.data.access import Query, SortOrder
from cortx.utils.log import Log
from csm.core.data.models.upgrade import UpdateStatusEntry
from csm.common.errors import CsmInternalError

class UpdateStatusRepository:
    """
    Repository that keeps a single instance of a UpdateStatusEntry model for each update type.
    """
    def __init__(self, storage: DataBaseProvider):
        self.db = storage

    @Log.trace_method(Log.DEBUG)
    async def get_current_model(self, update_type: str) -> UpdateStatusEntry:
        """
        Fetch the model. Returns None if it has never been saved or is deleted.
        :update_type: an identifier of the specific type of update (e.g. software, firmware, etc.)
        """
        query = Query().filter_by(Compare(UpdateStatusEntry.update_type, '=', update_type))
        query = query.order_by(UpdateStatusEntry.updated_at, SortOrder.DESC)
        model = next(iter(await self.db(UpdateStatusEntry).get(query)), None)
        return model

    @Log.trace_method(Log.DEBUG)
    async def save_model(self, model: UpdateStatusEntry):
        """
        Saves the model. If something already exists in the DB, it will be replaced.
        """
        if not isinstance(model, UpdateStatusEntry):
            raise CsmInternalError("It is only possible to save UpdateStatusEntry objects!")

        if not model.update_type:
            raise CsmInternalError("UpdateStatusEntry must not have empty update_type!")

        model.updated_at = datetime.datetime.now()
        await self.db(UpdateStatusEntry).store(model)
        Log.info(f"UpdateStatusEntry stored for {model.update_type}")

    @Log.trace_method(Log.DEBUG)
    async def drop_model(self, update_type: str) -> UpdateStatusEntry:
        """
        Drop the model instance from the DB (if it exists)
        :update_type: an identifier of the specific type of update (e.g. software, firmware, etc.)
        """
        # This is a workaround to delete all records - that is currently not directly
        # supported by the generic db
        _filter = Compare(UpdateStatusEntry.update_type, '=', update_type)
        Log.info(f"Deleting update status entry for update type {update_type}")
        await self.db(UpdateStatusEntry).delete(_filter)
        Log.info("Entry Deleted.")
