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
ALERTS_MSG_TOO_LONG_COMMENT = "alerts_too_long_comment"
ALERTS_MSG_RESOLVED_AND_ACKED_ERROR = "alerts_resolved_and_acked"
ALERTS_MSG_NON_SORTABLE_COLUMN = "alerts_non_sortable_column"



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
    
    async def update_new(self, filter, update_params):
        await self.db(AlertModel).update(filter, update_params)

    def _prepare_filters(self, time_range: DateTimeRange, show_all: bool = True,
            severity: str = None):

        query_conditions = []

        if time_range.start:
            query_conditions.append(Compare(AlertModel.updated_time, '>=', time_range.start))
        if time_range.end:
            query_conditions.append(Compare(AlertModel.updated_time, '<=', time_range.end))

        if not show_all:
            query_conditions.append(
                Or(Compare(AlertModel.resolved, '=', False), Compare(AlertModel.acknowledged, '=', False)))

        if severity:
            query_conditions.append(Compare(AlertModel.severity, '=', severity))

        return And(*query_conditions) if query_conditions else None

    async def retrieve_by_range(
            self, time_range: DateTimeRange, show_all: bool=True,
            severity: str=None, sort: Optional[SortBy]=None,
            limits: Optional[QueryLimits]=None) -> Iterable[AlertModel]:
        query_filter = self._prepare_filters(time_range, show_all, severity)
        query = Query().filter_by(query_filter)

        if limits and limits.offset:
            query = query.offset(limits.offset)

        if limits and limits.limit:
            query = query.limit(limits.limit)

        if sort:
            query = query.order_by(getattr(AlertModel, sort.field), sort.order)

        return await self.db(AlertModel).get(query)

    async def count_by_range(self, time_range: DateTimeRange, show_all: bool = True,
            severity: str = None) -> int:
        return await self.db(AlertModel).count(
            self._prepare_filters(time_range, show_all, severity))

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

    async def update_alert(self, alert_id, fields: dict):
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

        if alert.resolved and alert.acknowledged:
            raise CsmError("The alert is both resolved and acknowledged, it cannot be modified",
                ALERTS_MSG_RESOLVED_AND_ACKED_ERROR)

        if "comment" in fields:
            alert.comment = fields["comment"]
            max_len = const.ALERT_MAX_COMMENT_LENGTH
            if len(alert.comment) > max_len:
                raise CsmError("Alert size exceeds the maximum length of {}!".format(max_len),
                    ALERTS_MSG_TOO_LONG_COMMENT, {"max_length": max_len})

        if "acknowledged" in fields:
            if not isinstance(fields["acknowledged"], bool):
                raise TypeError("Acknowledged Value Must Be of Type Boolean.")
            alert.acknowledged = Alert.acknowledged.to_native(fields["acknowledged"])

        await self.repo.update(alert)
        return alert.to_primitive()

    async def fetch_all_alerts(self, duration, direction, sort_by, severity: Optional[str] = None,
                               offset: Optional[int] = None, show_all: Optional[bool] = True,
                               page_limit: Optional[int] = None) -> Dict:
        """
        Fetch All Alerts
        :param duration: time duration for range of alerts
        :param direction: direction of sorting asc/desc
        :param severity: if passed, alerts will be filtered by the passed severity
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

        if sort_by and sort_by not in const.ALERT_SORTABLE_FIELDS:
            raise CsmError("The specified column cannot be used for sorting",
                ALERTS_MSG_NON_SORTABLE_COLUMN)

        limits = None
        if offset is not None and offset > 1:
            limits = QueryLimits(page_limit, (offset - 1) * page_limit)
        elif page_limit is not None:
            limits = QueryLimits(page_limit, 0)

        alerts_list = await self.repo.retrieve_by_range(
            time_range,
            show_all,
            severity,
            SortBy(sort_by, SortOrder.ASC if direction == "asc" else SortOrder.DESC),
            limits
        )

        alerts_count = await self.repo.count_by_range(time_range, show_all, severity)
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
                self._run_coro(self.repo.store(alert))
                self._publish(alert)
                print("Alert Saved")
            else:
                print("Alert found")
                resolved = self._can_be_resolved(message, prev_alert)
                print(resolved)
        except Exception as e:
            Log.exception(e)

        return True

    def _can_be_resolved(self, new_alert, prev_alert):
        if not self._is_duplicate_alert(new_alert, prev_alert):
            if self._is_good_alert(new_alert):
                """
                If it is a good alert checking the state of previous alert.
                """
                if self._is_good_alert(prev_alert):
                    """ Previous alert is a good one so updating. """
                    self._update_and_save(new_alert, prev_alert)
                else:
                    """ Previous alert is a bad one so resolving it. """
                    self._resolve(new_alert, prev_alert)
            elif self._is_bad_alert(new_alert):
                """
                If it is a bad alert checking the state of previous alert.
                """
                if self._is_bad_alert(prev_alert):
                    """ Previous alert is a bad one so updating. """
                    self._update_and_save(new_alert, prev_alert)
                else:
                    """
                    Previous alert is a good one so updating and marking the
                    resolved status to False.
                    """
                    self._update_and_save(new_alert, prev_alert, True)        

    def _is_duplicate_alert(self, new_alert, prev_alert):
        """
        Check whether the alerts is duplicate or not based on state.
        :param alert : New Alert Dict
        :param prev_alert : Previous Alert object
        :return: boolean (True or False) 
        """
        ret = False
        if new_alert.get('state', "") == prev_alert.state:
            ret = True
        return ret

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
        update_params = {}
        if update_resolve:
            update_params["resolved"] = alert['resolved']
        else:
            update_params["resolved"] = prev_alert.resolved
        update_params["state"] = alert['state']
        update_params["severity"] = alert['severity']
        update_params["updated_time"] = int(time.time())
        print(update_params, prev_alert.hw_identifier) 
        filter = Compare(AlertModel.hw_identifier, '=', prev_alert.hw_identifier)
        self._run_coro(self.repo.update_new(filter, update_params))

    def _is_good_alert(self, alert):
        """
        Check whether the alert is good or not.
        :param alert : Alert object
        :return: boolean (True or False) 
        """
        ret = False
        if alert.get('state', "") in const.GOOD_ALERT:
            ret = True
        return ret

    def _is_bad_alert(self, alert):
        """
        Check whether the alert is bad or not.
        :param alert : Alert object
        :return: boolean (True or False) 
        """
        ret = False
        if alert.get('state', "") in const.BAD_ALERT:
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
            prev_alert.state = alert['state'] 
            prev_alert.severity = alert['severity'] 
            prev_alert.updated_time = int(time.time())


    def _resolve(self, alert, prev_alert):
        """
        Get the previous alert with the same alert_uuid.
        :param alert: Alert Object.
        :return: None
        """
        print(prev_alert.resolved)
        if not prev_alert.resolved:
            """
            Try to resolve the alert if the previous alert is bad and
            the current alert is good.
            """
            prev_alert.resolved = True 
            #prev_alert.resolved(True)
            self._update_and_save(alert, prev_alert)

    def _publish(self, alert):
        if self._handle_alert(alert.to_primitive()):
            self.unpublished_alerts.discard(alert)
