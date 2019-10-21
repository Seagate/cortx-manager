#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          alerts.py
 Description:       Services for alerts handling 

 Creation Date:     09/05/2019
 Author:            Alexander Nogikh
                    Prathamesh Rodi
                    Oleg Babin

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
from typing import Optional
from datetime import datetime, timedelta
from typing import Dict
from threading import Event, Thread
from csm.common.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from csm.core.blogic.models.alerts import IAlertStorage, Alert
from csm.common.errors import CsmNotFoundError, CsmError, InvalidRequest
from csm.core.blogic import const

ALERTS_MSG_INVALID_DURATION = "alert_invalid_duration"
ALERTS_MSG_NOT_FOUND = "alerts_not_found"
ALERTS_MSG_NOT_RESOLVED = "alerts_not_resolved"


class AlertsAppService(ApplicationService):
    """
        Provides operations on alerts without involving the domain specifics
    """

    def __init__(self, storage: IAlertStorage):
        self._storage = storage

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
        alert = await self._storage.retrieve(int(alert_id))
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)

        if "comment" in fields:
            # TODO: Alert should contain such fields directly, not as a
            #   dictionary accessible by data() method
            alert.data()["comment"] = fields["comment"]
        if "acknowledged" in fields:
            if not isinstance(fields["acknowledged"], bool):
                raise TypeError("Acknowledged Value Must Be of Type Boolean.")
            alert.data()["acknowledged"] = fields["acknowledged"]

        await self._storage.update(alert)
        return alert.data()

    async def fetch_all_alerts(self, duration, direction, sort_by,
                               offset: Optional[int],
                               page_limit: Optional[int]) -> Dict:
        """
        Fetch All Alerts
        :param duration: time duration for range of alerts
        :param direction: direction of sorting asc/desc
        :param sort_by: key by which sorting needs to be performed.
        :param offset: offset page (1-based indexing)
        :param page_limit: no of records to be displayed on a page.
        :return: :type:list
        """
        time_range = None
        if duration:  # Filter
            # TODO: time format can generally be API-dependent. Better pass here an
            # already parsed TimeDelta object.
            time_duration = int(re.split(r'[a-z]', duration)[0])
            time_format = re.split(r'[0-9]', duration)[-1]
            dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            if time_format not in dur.keys():
                raise InvalidRequest(
                    "Invalid Parameter for Duration", ALERTS_MSG_INVALID_DURATION)
            
            start_time = (datetime.utcnow() - timedelta(
                **{dur[time_format]: time_duration}))
            time_range = DateTimeRange(start_time, None)

        limits = None
        if offset is not None and offset > 1:
            limits = QueryLimits(page_limit, (offset - 1) * page_limit)
        elif page_limit is not None:
            limits = QueryLimits(page_limit, 0)

        alerts_list = await self._storage.retrieve_by_range(
            time_range,
            SortBy(sort_by, SortOrder.ASC if direction == "asc" else SortOrder.DESC),
            limits
        )

        alerts_count = await self._storage.count_by_range(time_range)
        return {
            "total_records": alerts_count,
            "alerts": [alert.data() for alert in alerts_list]
        }

    async def fetch_alert(self, alert_id):
        """
            Fetch a single alert by its key

            :param str alert_id: A unique identifier of the requried alert
            :returns: Alert object or None
        """
        # This method is for debugging purposes only
        alert = await self._storage.retrieve(alert_id)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)
        return alert.data()


class AlertMonitorService(Service):
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

    def __init__(self, storage: IAlertStorage, plugin, alert_handler_cb):
        """
        Initializes the Alert Plugin
        """
        self._alert_plugin = plugin
        self._handle_alert = alert_handler_cb
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._loop = asyncio.get_event_loop()
        self._storage = storage

    def init(self):
        """
        This function will scan the DB for pending alerts and send it over the
        back channel.
        """

        def nonpublished(_, alert):
            return not alert.is_published()

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
                self._monitor_thread = Thread(target=self._monitor,
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

    def save_alert(self, message) -> Alert:
        # This implementation uses threads, but storage is supposed to be async
        # So we put the task onto the main event loop and wait for its completion

        alert = Alert(message)
        alert_task = asyncio.run_coroutine_threadsafe(
            self._storage.store(alert), self._loop)

        alert_task.result()  # wait for completion
        return alert

    def get_alert(self, alert_id) -> Optional[Alert]:
        """
        Get the single from the DB for the alert_id
        :param alert_id: ID for Alerts.
        :return: Alert Object
        """
        alert_task = asyncio.run_coroutine_threadsafe(
            self._storage.retrieve(alert_id, {}), self._loop)
        result = alert_task.result(timeout=2)
        return  result # wait for completion

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
        """
        Before storing the alert let us fisrt try to resolve it.
        We will only resolve the alert if it is a good one.
        """
        if alert.data().get(const.ALERT_STATE, "") in const.GOOD_ALERT:
            self._resolve(alert)
        alert = self.save_alert(message)
        self._publish(alert)
        return True


    def _resolve(self, alert) -> None:
        """
        Get the previous alert with the same alert_uuid.
        :param alert: Alert Object.
        :return: None
        """
        prev_alert = self.get_alert(alert.key())
        if prev_alert:
            if prev_alert.data().get('state', "") \
                in const.BAD_ALERT and not prev_alert.is_resolved():
                """
                Try to resolve the alert if the previous alert is bad and
                the current alert is good.
                """
                alert.data()['resolved'] = 1
                alert.resolved()

    def _publish(self, alert):
        if self._handle_alert(alert.data()):
            alert.publish()
