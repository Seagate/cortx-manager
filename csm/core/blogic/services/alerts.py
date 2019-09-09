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
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict
from csm.core.repositories.alerts import SyncAlertStorage

from csm.common.errors import CsmNotFoundError, CsmError

ALERTS_ERROR_INVALID_DURATION = "alert_invalid_duration"
ALERTS_ERROR_NOT_FOUND="alerts_not_found"
ALERTS_ERROR_NOT_RESOLVED="alerts_not_resolved"


class AlertsAppService:
    """
        Provides operations on alerts without involving the domain specifics
    """

    # TODO: In the case of alerts, we probably do not need another alert-related
    # service

    def __init__(self, storage: SyncAlertStorage):
        self._storage = storage

    async def _call_nonasync(self, function, *args):
        """
            This function allows to await on synchronous code.
            It won't be needed once we switch to asynchronous code everywhere.

            :param function: A callable
            :param args: Positional arguments that will be passed to the
                         function
            :returns: the result returned by 'function'
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, function, *args)

    async def update_alert(self, alert_id, fields):
        """
        Update the Data of Specific Alerts
        :param alert_id: id for the alert
        :param fields: A dictionary containing fields to update.
                Currently it supports "comment" and "acknowledged" fields only.
                "comment" - string, can be empty
                "acknowledged" - boolean
        :return:
        """
        alert = await self._call_nonasync(self._storage.retrieve, alert_id)
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

        await self._call_nonasync(self._storage.update, alert)
        return alert.data()

    async def fetch_all_alerts(self, duration, direction, sort_by, offset,
                               page_limit) -> Dict:
        """
        Fetch All Alerts
        :param duration: time duration for range of alerts
        :param direction: direction of sorting asc/desc
        :param sort_by: key by which sorting needs to be performed.
        :param offset: offset page
        :param page_limit: no of records to be displayed on page.
        :return: :type:list
        """
        # TODO: The storage must provide a function to fetch alerts with respect to
        # parameters and orderings requried by the business logic.
        alerts_obj = await self._call_nonasync(self.service.fetch_all_alerts)
        if alerts_obj:
            reverse = True if direction == 'desc' else False
            alerts_obj = sorted(alerts_obj, key=lambda item: item.data()[sort_by],
                                reverse=reverse)
            if duration:  # Filter
                # TODO: time format can generally be API-dependent. Better pass here an already
                # parsed TimeDelta object.
                time_duration = int(re.split(r'[a-z]', duration)[0])
                time_format = re.split(r'[0-9]', duration)[-1]
                dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
                if time_format not in dur.keys():
                    raise CsmError(ALERT_ERROR_INVALID_DURATION,
                            "Invalid Parameter for Duration")
                end_time = datetime.now().timestamp()
                start_time = (datetime.utcnow() - timedelta(
                    **{dur[time_format]: time_duration})).timestamp()
                alerts_obj = list(
                    filter(lambda x: start_time < x['created_time'] < end_time,
                           alerts_obj))
            if offset and int(offset) >= 1:
                offset = int(offset)
                if page_limit and int(page_limit) > 0:
                    page_limit = int(page_limit)
                    alerts_obj = [alerts_obj[i:i + page_limit] for i in
                                  range(0, len(alerts_obj), page_limit)]

                alerts_obj = alerts_obj[int(offset) - 1]

        return {"total_records": len(alerts_obj), "alerts": alerts_obj.data()}

    async def fetch_alert(self, alert_id):
        """
            Fetch a single alert by its key

            :param str alert_id: A unique identifier of the requried alert
            :returns: Alert object or None
        """
        # This method is for debugging purposes only
        alert = await self._call_nonasync(self._storage.retrieve, alert_id))
        if not alert:
            raise CsmNotFoundError(ALERTS_ERROR_NOT_FOUND, "Alert is not found")
        return alert.data()


class AlertMonitorService(object):
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