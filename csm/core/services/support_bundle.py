#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          api_client.py
 Description:       Infrastructure for invoking business logic locally or
                    remotely or various available channels like REST.

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from eos.utils.data.db.db_provider import DataBaseProvider
from csm.core.blogic.models.support_bundle import SupportBundleModel
from eos.utils.data.access import Query
from eos.utils.data.access.filters import Compare

class SupportBundleRepository:
    def __init__(self, storage: DataBaseProvider):
        self.db = storage

    async def retrieve_all(self, bundle_id) -> [SupportBundleModel]:
        query = Query().filter_by(Compare(SupportBundleModel.bundle_id, '=',
                                          bundle_id))
        return await self.db(SupportBundleModel).get(query)
