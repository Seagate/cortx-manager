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

        def _check_alert_date(datetime: datetime):
            if (time_range.start is not None) and datetime < time_range.start:
                return False
            if (time_range.end is not None) and datetime > time_range.end:
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
                            key=lambda item: item.data()[sort.field],
                            reverse=(sort.order == SortOrder.ASC))

        if limits is not None:
            slice_from = limits.offset or 0
            slice_to = slice_from + (limits.limit or 0)
            alerts = alerts[slice_from:slice_to]

        return alerts

    async def count_by_range(self, time_range: DateTimeRange):
        return len(await self._retrieve_by_range(time_range))

    # todo: Remove the Below Commeted code this is just to dump the data while starting the server.
    # @staticmethod
    # def random_date():
    #     """
    #     This function will return a random datetime between two datetime
    #     objects.
    #     """
    #     from random import randrange
    #     from datetime import timedelta, datetime
    #     start = datetime.utcnow() - timedelta(days=2)
    #     end = datetime.utcnow()
    #     delta = end - start
    #     int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    #     random_second = randrange(int_delta)
    #     return start + timedelta(seconds=random_second)
    #
    #
    # def add_data(self):
    #     x = {
    #         "id": 0,
    #         "alert_uuid": 0,
    #         "status": "Up",
    #         "type": "hw",
    #         "enclosure_id": 0,
    #         "module_name": "",
    #         "description": "",
    #         "health": "OK",
    #         "health_recommendation": "",
    #         "location": "Enclosure 0 - Right",
    #         "resolved": 0,
    #         "acknowledged": 0,
    #         "severity": 1,
    #         "state": "fault_resolved",
    #         "extended_info": {
    #             "resource_type": "fru",
    #             "position": "Right",
    #             "durable-id": "psu_0.1",
    #             "other_details": {
    #                 "dc12v": 0,
    #                 "dctemp": 0,
    #                 "vendor": "",
    #                 "description": "",
    #                 "dc33v": 0,
    #                 "mfg-vendor-id": "",
    #                 "fru-shortname": "",
    #                 "serial-number": "DHSILTC-1913PIZZAS",
    #                 "mfg-date": "N/A",
    #                 "part-number": "FRUKE18-01",
    #                 "model": "FRUKE18-01",
    #                 "revision": "A",
    #                 "dc5v": 0,
    #                 "dc12i": 0,
    #                 "dc5i": 0
    #             }
    #         },
    #         "module_type": "psu",
    #         "updated_time": "2019-08-28 11:10:09.137026",
    #         "created_time": "2019-07-25 11:23:28.563236"
    #     }
    #     for i in range(0, 1000):
    #         x['id'] = i
    #         x["alert_uuid"] = i
    #         x['updated_time'] = SyncAlertStorage.random_date().timestamp()
    #         x['created_time'] = SyncAlertStorage.random_date().timestamp()
    #         self._kvs.put(i, x)

# TODO: Implement async alert storage after
#       moving from threads to asyncio
#
# class AsyncAlertStorage:
#     def __init__(self, kvs):
#         self._kvs = kvs
#         self._id = 0

#     def nextid(self):
#         result = self._id
#         self._id += 1
#         return result

#     async def store(self, alert):
#         key = self.nextid()
#         alert.store(key)
#         await self._kvs.put(alert.key(), alert)

#     async def retrieve(self, key):
#         return await self._kvs.get(key)

#     async def select(self, predicate):
#         return (alert
#             async for key, alert in self._kvs.items()
#                 if predicate(key, alert))


