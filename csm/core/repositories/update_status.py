#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          update_status.py
 Description:       Services common for all CSM-related updates

 Creation Date:     03/24/2020
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import datetime
from eos.utils.data.db.db_provider import DataBaseProvider
from eos.utils.data.access.filters import Compare, And, Or
from eos.utils.data.access import Query, SortOrder
from eos.utils.log import Log
from csm.core.data.models.upgrade import UpdateStatusEntry


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

    @Log.trace_method(Log.DEBUG)
    async def drop_model(self, update_type: str) -> UpdateStatusEntry:
        """
        Drop the model instance from the DB (if it exists)
        :update_type: an identifier of the specific type of update (e.g. software, firmware, etc.)
        """
        # This is a workaround to delete all records - that is currently not directly
        # supported by the generic db
        filter = Compare(UpdateStatusEntry.update_type, '=', update_type)
        await self.db(UpdateStatusEntry).delete(filter)
