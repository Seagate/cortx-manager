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

import errno
import threading
from datetime import datetime

from csm.common.errors import CsmError
from csm.common.log import Log
from csm.core.blogic import const
from csm.core.blogic.storage import SyncInMemoryKeyValueStorage

class Alert(object):
    """ Represents an alert to be sent to front end """

    def __init__(self, data):
        """ Setting up the key with alert_uuid from the CSM json. """
        self._key = data.get(const.ALERT_UUID, const.ALERT_INT_DEFAULT)
        self._data = data
        self._timestamp = datetime.utcnow()
        self._published = False
        self._resolved = False

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
        self._published = True

    def ispublished(self):
        return self._published

    def resolved(self):
        self._resolved = True

    def isResolved(self):
        return self._resolved

    def show(self, **kwargs):
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
        self._kvs.put(alert.key(), alert)

    def retrieve(self, key):
        return self._kvs.get(key)

    def select(self, predicate):
        return (alert
                for key, alert in self._kvs.items()
                if predicate(key, alert))
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

    def __init__(self, plugin, alert_handler_cb):
        """
        Initializes the Alert Plugin
        """
        self._alert_plugin = plugin
        self._handle_alert = alert_handler_cb
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._storage = SyncAlertStorage(SyncInMemoryKeyValueStorage())

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
            1. Resolve the alerts.
            2. Store the alert to Alert DB.
            3. Publish the alert over web sockets.
            4. Return a boolean value to signal whether the plugin
               should acknowledge the alert to the RabbitMQ.
        """
        try:
            alert = Alert(message)
            """
            Before storing the alert let us fisrt try to resolve it.
            We will only resolve the alert if it is a good one.
            """
            if alert.data().get(const.ALERT_STATE, "") in const.GOOD_ALERT:
                self._resolve(self._storage, alert)
            self._storage.store(alert)
            self._publish(alert)
        except Exception as e:
            Log.exception(e)
        return False

    def _publish(self, alert):
        if self._handle_alert(alert.data()):
            alert.publish()

    def _resolve(self, storage, alert):
        """
        Get the previous alert with the same alert_uuid.
        """
        prev_alert = storage.retrieve(alert.key())
        if prev_alert and prev_alert.data().get('state', "") \
                in const.BAD_ALERT and not prev_alert.isResolved():
            """
            Try to resolve the alert if the previous alert is bad and
            the current alert is good.
            """
            alert.data()['resolved'] = 1
            alert.resolved()
