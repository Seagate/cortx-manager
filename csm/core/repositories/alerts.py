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
from copy import  deepcopy
from typing import Optional, Iterable
from csm.core.blogic.models.alerts import IAlertStorage, Alert
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange


class AlertSimpleStorage(IAlertStorage):
    def __init__(self, kvs):
        self._kvs = kvs
        self._id = 0

    async def _nextid(self):
        result = self._id
        self._id += 1
        return result

    async def store(self, alert):
        key = alert.key()
        if key is None:
            key = str(await self._nextid())
            alert.store(key)
        self._kvs.put(key, deepcopy(alert))

    async def retrieve(self, key, def_val=None):
        return self._kvs.get(key, def_val)

    async def retrieve_all(self):
        return list(map(lambda x: x[1], self._kvs.items()))

    async def update(self, alert):
        self._kvs.put(alert.key(), alert)

    async def select(self, predicate):
        return (alert
                for key, alert in self._kvs.items()
                if predicate(key, alert))

    async def _retrieve_by_range(self, time_range: DateTimeRange):

        def _check_alert_date(epoch_time):
            datetime_obj = datetime.utcfromtimestamp(epoch_time)

            if (time_range.start is not None) and datetime_obj < time_range.start:
                return False
            if (time_range.end is not None) and datetime_obj > time_range.end:
                return False

            return True

        alerts = await self.retrieve_all()
        if time_range is not None:
            return [x for x in alerts if _check_alert_date(x.data()['created_time'])]
        else:
            return alerts

    async def retrieve_by_range(
            self, time_range: DateTimeRange, sort: Optional[SortBy],
            limits: Optional[QueryLimits]) -> Iterable[Alert]:
        alerts = await self._retrieve_by_range(time_range)
        if sort is not None:
            alerts = sorted(alerts,
                            key=lambda item: item.data().get(sort.field,
                                "created_time"),
                            reverse=(sort.order == SortOrder.ASC))

        if limits is not None:
            slice_from = limits.offset or 0
            slice_to = slice_from + (limits.limit or 0)
            alerts = alerts[slice_from:slice_to]

        return alerts

    async def count_by_range(self, time_range: DateTimeRange):
        return len(await self._retrieve_by_range(time_range))
    