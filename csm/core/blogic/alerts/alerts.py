"""
 ****************************************************************************
 Filename:          alerts.py
 Description:       Contains functionality for alert plugin.

 Creation Date:     12/08/2019
 Author:            Pawan Kumar Srivastava

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
from csm.common.errors import CsmError, CsmNotFoundError
from csm.common.log import Log
from datetime import datetime
from typing import Optional
import json
import threading
import errno

class Alert(object):
    """ Represents an alert to be sent to front end """

    def __init__(self, data):
        self._key = None
        self._data = data
        self._timestamp = datetime.utcnow()
        self._publushed = False

    def key(self):
        return self._key

    def data(self):
        return self._data

    def timestamp(self):
        return self._timestamp

    def store(self, key):
        self._key = key

    def isstored(self):
        return self._key != None

    def publish(self):
        self._publushed = True

    def ispublished(self):
        return self._publushed

    def get(self, **kwargs):
        # TODO
        raise CsmError(errno.ENOSYS, 'Alert.get() not implemented')

    def acknowledge(self, id):
        # TODO
        raise CsmError(errno.ENOSYS, 'Alert.acknowledge() not implemented')

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

ALERTS_ERROR_NOT_FOUND="alerts_not_found"
ALERTS_ERROR_NOT_RESOLVED="alerts_not_resolved"


# TODO: make it async once AsyncAlertStorage is implemented
class AlertsService:

    """
        The class contains all alert-related actions that are supposed to be callable
        by upper layer(s) of the application.
    """

    def __init__(self, storage: SyncAlertStorage):
        self._storage = storage

    def update_alert(self, alert_id, fields: dict):
        """
            Update alert fields

            :param str alert_id: A unique identifier of an alert to update
            :param dict fields:  A dictionary containing fields to update.
                Currently it supports "comment" and "acknowledged" fields only.
                "comment" - string, can be empty
                "acknowledged" - boolean
            :returns: the updated Alert object
            :raises CsmError:
        """
        alert = self._storage.retrieve(alert_id)
        if not alert:
            raise CsmNotFoundError(ALERTS_ERROR_NOT_FOUND, "Alert was not found")

        if "comment" in fields:
            # TODO: Alert should contain such fields directly, not as a
            #   dictionary accessible by data() method
            alert.data()["comment"] = fields["comment"]

        if "acknowledged" in fields:
            # TODO: We need some common code that does such conversions
            new_value = fields["acknowledged"] == True \
                        or fields["acknowledged"] == "1" \
                        or fields["acknowledged"] == "true"

            if new_value and not alert.data()["resolved"]:
                raise CsmError(ALERTS_ERROR_NOT_RESOLVED,
                        "Unresolved alerts cannot be acknowledged")

            alert.data()["acknowledged"] = new_value

        self._storage.update(alert)
        return alert

    def fetch_all_alerts(self) -> list:
        """
        Fetch all Alerts
        :return: Alerts Object or Blank dict
        """
        return self._storage.retrieve_all()

    def fetch_alert(self, alert_id) -> Optional[Alert]:
        """
            Fetch a single alert by its key

            :param str alert_id: A unique identifier of the requried alert
            :returns: Alert object or None
        """
        return self._storage.retrieve(alert_id)

class AlertMonitor(object):
    """
    Alert Monitor works with AmqpComm to monitor alerts. 
    When Alert Monitor receives a subscription request, it scans the DB and 
    sends all pending alerts. It is assumed currently that there can be only 
    one subscriber at any given point of time. 
    Then it waits for AmqpComm to notice if there are any new alert. 
    Alert Monitor takes action on the received alerts using a callback. 
    Actions include (1) storing on the DB and (2) sending to subscribers, i.e.
    web server. 
    """

    def __init__(self, storage: SyncAlertStorage, plugin, alert_handler_cb):
        """
        Initializes the Alert Plugin
        """
        self._alert_plugin = plugin
        self._handle_alert = alert_handler_cb
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._storage = storage

    def init(self):
        """
        This function will scan the DB for pending alerts and send it over the
        back channel.
        """

        def nonpublished(_, alert):
            return not alert.ispublished()

        for alert in self._storage.select(nonpublished):
            self._publish(alert)

    def _monitor(self):
        """
        This method acts as a thread function. 
        It will monitor the alert plugin for alerts.
        This method passes consume_alert as a callback function to alert plugin.
        """
        self._thread_running = True
        self._alert_plugin.init(callback_fn=self._consume)
        self._alert_plugin.process_request(cmd='listen')

    def start(self):
        """
        This method creats and starts an alert monitor thread
        """
        try:
            if not self._thread_running and not self._thread_started:
                self._monitor_thread = threading.Thread(target=self._monitor,
                                                        args=())
                self._monitor_thread.start()
                self._thread_started = True
        except Exception as e:
            Log.exception(e)

    def stop(self):
        try:
            self._alert_plugin.stop()
            self._monitor_thread.join()
            self._thread_started = False
            self._thread_running = False
        except Exception as e:
            Log.exception(e)

    def _consume(self, message):
        """
        This is a callback function which will receive
        a message from the alert plugin as a dictionary.
        The message is already convrted to CSM schema.
            1. Store the alert to Alert DB.
            2. Publish the alert over web sockets.
            3. Return a boolean value to signal whether the plugin
               should acknowledge the alert to the RabbitMQ.
        """
        alert = Alert(message)
        self._storage.store(alert)
        self._publish(alert)
        return True

    def _publish(self, alert):
        if self._handle_alert(alert.data()):
            alert.publish()
