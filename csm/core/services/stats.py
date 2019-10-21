#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          stats.py
 Description:       Services for stats handling

 Creation Date:     10/16/2019
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


"""
    This is sample service implementation
"""


# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
import asyncio
import re
from typing import Optional
from datetime import datetime, timedelta
from typing import Dict
from threading import Event, Thread
from csm.common.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from csm.common.errors import CsmNotFoundError, CsmError, InvalidRequest
from csm.core.blogic import const

STATS_DATA_MSG_NOT_FOUND = "stats_not_found"


class StatsAppService(ApplicationService):
    """
    Provides operations on stats without involving the domain specifics
    """

    """
    def __init__(self, storage: IAlertStorage):
        self._storage = storage
    """

    async def get_all(self, **kwargs) -> Dict:
        """
        Fetch All stats
        :param kwargs
        :return: :type:Dict
        """
        return {
            "total_records": "1",
            "stats": "success",
            "duration": kwargs.get('duration', None),
            "offset": kwargs.get('offset', None)
        }

    async def get(self, **kwargs) -> Dict:
        """
        Fetch specific stat
        :return: :type:list
        """
        return {
            "stat_id": kwargs['stat_id'],
            "stats": "success"
        }
