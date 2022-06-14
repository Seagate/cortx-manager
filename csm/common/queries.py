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

from datetime import datetime
from typing import Optional
from cortx.utils.data.access import SortOrder


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
