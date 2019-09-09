

class SyncAlertStorage:
    def __init__(self, kvs):
        self._kvs = kvs
        self._id = 0

    def _nextid(self):
        result = self._id
        self._id += 1
        return result

    def store(self, alert):
        key = str(self._nextid())
        alert.store(key)
        self._kvs.put(key, alert)

    def retrieve(self, key):
        return self._kvs.get(key)

    def retrieve_all(self):
        return list(map(lambda x: x[1], self._kvs.items()))

    def update(self, alert):
        self._kvs.put(alert.key(), alert)

    def select(self, predicate):
        return (alert
                for key, alert in self._kvs.items()
                if predicate(key, alert))

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


