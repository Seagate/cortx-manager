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
from datetime import datetime, timedelta, timezone
from typing import Dict
from threading import Event, Thread
from csm.common.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from csm.core.blogic.models.alerts import IAlertStorage, Alert
from csm.common.errors import CsmNotFoundError, CsmError, InvalidRequest
from csm.core.blogic import const
import time
from csm.core.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.core.data.access.filters import Compare, And, Or
from csm.core.data.access import Query, SortOrder
from csm.core.blogic.models.alerts import AlertModel
from csm.common import queries
from schematics import Model
from schematics.types import StringType, BooleanType, IntType
from typing import Optional, Iterable


ALERTS_MSG_INVALID_DURATION = "alert_invalid_duration"
ALERTS_MSG_NOT_FOUND = "alerts_not_found"
ALERTS_MSG_NOT_RESOLVED = "alerts_not_resolved"



class AlertRepository(IAlertStorage):
    def __init__(self, storage: DataBaseProvider):
        self.db = storage

    async def store(self, alert: AlertModel):
        await self.db(AlertModel).store(alert)

    async def retrieve(self, alert_id) -> AlertModel:
        query = Query().filter_by(Compare(AlertModel.alert_uuid, '=', alert_id))
        return next(iter(await self.db(AlertModel).get(query)), None)

    async def retrieve_by_hw(self, hw_id) -> AlertModel:
        #import pdb
        #pdb.set_trace()
        query = Query().filter_by(Compare(AlertModel.hw_identifier, '=',
            str(hw_id)))
        return next(iter(await self.db(AlertModel).get(query)), None)

    async def update(self, alert: AlertModel):
        await self.db(AlertModel).store(alert)

    def _prepare_filters(self, time_range: DateTimeRange):
        query_conditions = []

        if time_range.start:
            query_conditions.append(Compare(AlertModel.updated_time, '>=', time_range.start))
        if time_range.end:
            query_conditions.append(Compare(AlertModel.updated_time, '<=', time_range.end))

        return And(*query_conditions) if query_conditions else None

    async def retrieve_by_range(
            self, time_range: DateTimeRange, sort: Optional[SortBy],
            limits: Optional[QueryLimits]) -> Iterable[AlertModel]:
        query_filter = self._prepare_filters(time_range)
        query = Query().filter_by(query_filter)

        if limits and limits.offset:
            query = query.offset(limits.offset)

        if limits and limits.limit:
            query = query.limit(limits.limit)

        if sort:
            query = query.order_by(getattr(AlertModel, params.sort_by), sort.order)

        return await self.db(AlertModel).get(query)

    async def count_by_range(self, time_range: DateTimeRange):
        return await self.db(AlertModel).count(self._prepare_filters(time_range))

    async def retrieve_all(self) -> list:
        """
        Retrieves all the
        """
        pass

class AlertsAppService(ApplicationService):
    """
        Provides operations on alerts without involving the domain specifics
    """

    def __init__(self, repo: AlertRepository):
        self.repo = repo

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

        alert = await self.repo.retrieve(alert_id)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)

        if "comment" in fields:
            alert.comment = fields["comment"]

        if "acknowledged" in fields:
            if not isinstance(fields["acknowledged"], bool):
                raise TypeError("Acknowledged Value Must Be of Type Boolean.")
            alert.acknowledged = Alert.acknowledged.to_native(fields["acknowledged"])

        await self.repo.update(alert)
        return alert.to_primitive()

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
            start_time = (datetime.utcnow() - timedelta(
                **{dur[time_format]: time_duration}))
            time_range = DateTimeRange(start_time, None)

        limits = None
        if offset is not None and offset > 1:
            limits = QueryLimits(page_limit, (offset - 1) * page_limit)
        elif page_limit is not None:
            limits = QueryLimits(page_limit, 0)

        alerts_list = await self.repo.retrieve_by_range(
            time_range,
            SortBy(sort_by, SortOrder.ASC if direction == "asc" else SortOrder.DESC),
            limits
        )

        alerts_count = await self.repo.count_by_range(time_range)
        return {
            "total_records": alerts_count,
            "alerts": [alert.to_primitive() for alert in alerts_list]
        }

    async def fetch_alert(self, alert_id):
        """
            Fetch a single alert by its key

            :param str alert_id: A unique identifier of the requried alert
            :returns: Alert object or None
        """
        # This method is for debugging purposes only
        alert = await self.repo.retrieve(alert_id)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)
        return alert.to_primitive()


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

    def __init__(self, repo: AlertRepository, plugin, alert_handler_cb):
        """
        Initializes the Alert Plugin
        """
        self._alert_plugin = plugin
        self._handle_alert = alert_handler_cb
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._loop = asyncio.get_event_loop()
        self.repo = repo
        self.unpublished_alerts = set() 

    def init(self):
        """
        This function will scan the DB for pending alerts and send it over the
        back channel.
        """
        """
        def nonpublished(_, alert):
            return not alert.is_published()

        for alert in self._storage.select(nonpublished):
            self._publish(alert)
        """
        while self.unpublished_alerts:
            self._publish(self.pop())

        #for alerts in self.unpublished_alerts:
        #    self._publish(alerts)
        print("Inside Init")

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

    def save_alert(self, alert):
        # This implementation uses threads, but storage is supposed to be async
        # So we put the task onto the main event loop and wait for its completion

        alert_task = asyncio.run_coroutine_threadsafe(
            self._storage.store(alert), self._loop)

        alert_task.result()  # wait for completion

    def _run_coro(self, coro):
        task = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return task.result()

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

    def get_all_alerts(self):
        """
        Get the list of all the alerts from storage
        :param None
        :return: list of Alert objects
        """
        alert_task = asyncio.run_coroutine_threadsafe\
                (self._storage.retrieve_all(), self._loop)
        result = alert_task.result(timeout=2)
        return result

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
        #alert = AlertModel(message)
        print("Incoming Alert ---", message)
        prev_alert = None
        """
        Before storing the alert let us fisrt try to resolve it.
        We will only resolve the alert if it is a good one.
        Logic implemented for resolving or updating alerts -
        1.) If there is no previous alert we save and publish the alert.
        2.) If there is a previous alert we will only proceed if the state of the
        new alert is different from the previous one (check for duplicate).
        3.) If a good alert comes we search of previous alert for the same hw.
        4.) If a good previous alert(another state) is found we update the 
        previous alert.
        5.) If a bad previous alert is found we resolve the previous alert.
        6.) If a bad alert comes we search for previous alert for the same hw.
        7.) If a bad previous alert(another state) is found we update
        the previous alert.
        8.) If a good previous alert is found we update the previous alert and
        set the resolved state to False.
        """
        """ Fetching the previous alert. """
        try:
            message['extended_info'] = str(message.get('extended_info'))
            """
            filter = Compare(AlertModel.hw_identifier, '=',
                    message.get(const.ALERT_HW_IDENTIFIER, ""))
            query = Query().filter_by(filter)
            alert = next(iter(self._run_coro(self._storage(AlertModel).get(query))), None)
            """
            #print(message.get(const.ALERT_HW_IDENTIFIER, ""))
            prev_alert = self._run_coro(self.repo.retrieve_by_hw\
                    (message.get(const.ALERT_HW_IDENTIFIER, "")))
            #print("Prev - ", prev_alert.alert_uuid, prev_alert.hw_identifier)
            if not prev_alert:
                alert = AlertModel(message)
                self.unpublished_alerts.add(alert)
                self._save_and_publish(alert)
                print("Alert Saved")
            else:
                print("Alert found")
        except Exception as e:
            Log.exception(e)

        return True

    def _save_and_publish(self, alert):
        """
        Save the alerts to storage and publish them onto WS.
        :param alert : Alert object
        :return: None
        """
        self._run_coro(self.repo.store(alert))
        self._publish(alert)

    def _update_and_save(self, alert, prev_alert, update_resolve=False):
        """
        Update the alerts to storage.
        :param alert : Alert object
        :param prev_alert : Previous Alert object
        :param update_resolve : If set to True, we will mark resolved state to
        False
        :return: None
        """
        if update_resolve:
            prev_alert.data()['resolved'] = alert.data()['resolved']
            prev_alert.resolved(False)
        self._update_prev_alert(alert, prev_alert)
        self.save_alert(prev_alert)

    def _is_duplicate_alert(self, alert, prev_alert):
        """
        Check whether the alerts is duplicate or not based on state.
        :param alert : Alert object
        :param prev_alert : Previous Alert object
        :return: boolean (True or False) 
        """
        ret = False
        if alert.data().get('state', "") == \
                prev_alert.data().get('state', ""):
            ret = True
        return ret

    def _is_good_alert(self, alert):
        """
        Check whether the alert is good or not.
        :param alert : Alert object
        :return: boolean (True or False) 
        """
        ret = False
        if alert.data().get('state', "") in const.GOOD_ALERT:
            ret = True
        return ret

    def _is_bad_alert(self, alert):
        """
        Check whether the alert is bad or not.
        :param alert : Alert object
        :return: boolean (True or False) 
        """
        ret = False
        if alert.data().get('state', "") in const.BAD_ALERT:
            ret = True
        return ret

    def _get_prev_alert(self, alert):
        """
        Get the previously stored alert for the hw
        :param alert: Alert's object.
        :return: Alert Object
        """
        prev_alert = None
        alert_list = self.get_all_alerts()
        for value in alert_list:
            if value.data().get("hw_identifier", '') == \
                    alert.data().get("hw_identifier", ''):
                prev_alert = value
                break

        return prev_alert

    def _update_prev_alert(self, alert, prev_alert):
        """
        Update the previously stored alert for the hw
        :param alert: Alert's object.
        :param prev_alert: Previous Alert's object.
        :return: None
        """
        if not prev_alert == None:
            prev_alert.data()['state'] = alert.data()['state'] 
            prev_alert.data()['severity'] = alert.data()['severity'] 
            prev_alert.data()['updated_time'] = int(time.time())


    def _resolve(self, alert, prev_alert):
        """
        Get the previous alert with the same alert_uuid.
        :param alert: Alert Object.
        :return: None
        """
        if not prev_alert.is_resolved():
            """
            Try to resolve the alert if the previous alert is bad and
            the current alert is good.
            """
            prev_alert.data()['resolved'] = True 
            prev_alert.resolved(True)
            self._update_and_save(alert, prev_alert)

    def _publish(self, alert):
        if self._handle_alert(alert):
            self.unpublished_alerts.discard(alert)
