#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          queries.py
 Description:       Contains common classes that might be useful for data querying

 Creation Date:     09/10/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


from datetime import datetime
from enum import Enum
from typing import Optional
from eos.utils.data.access import SortOrder

class SortBy:
    def __init__(self, field, order: SortOrder):
        self.field = field
        self.order = order


class QueryLimits:
    def __init__(self, limit: Optional[int], offset: Optional[int]):
        self.limit = limit
        self.offset = offset


class DateTimeRange:
    def __init__(self, start: Optional[datetime], end: Optional[datetime]):
        self.start = start
        self.end = end
