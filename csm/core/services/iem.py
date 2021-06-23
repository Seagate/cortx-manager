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

from csm.common.services import ApplicationService, Service
from cortx.utils.iem_framework import EventMessage
from cortx.utils.iem_framework.error import EventMessageError
from typing import NamedTuple
from csm.common.observer import Observable
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.core.blogic.models.alerts import IAlertStorage
import time
from csm.core.blogic.models.alerts import AlertModel, AlertsHistoryModel
from datetime import datetime, timedelta, timezone
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from cortx.utils.data.access.filters import Compare, And, Or
from cortx.utils.data.access import Query, SortOrder
from csm.core.blogic.models.alerts import AlertModel, AlertsHistoryModel
from csm.core.blogic.models.comments import CommentModel
from csm.core.services.users import UserManager
from csm.common import queries
from schematics import Model
from schematics.types import StringType, BooleanType, IntType
from typing import Optional, Iterable, Dict
from csm.common.payload import Payload, Json, JsonMessage
import asyncio
from cortx.utils.log import Log
from threading import Thread

class IemPayload(NamedTuple):
    severity: str
    module: str
    event_id: int
    message_blob: str

class IemRepository(IAlertStorage):
    def __init__(self, storage: DataBaseProvider):
        self._db = storage

    async def store(self, alert: AlertModel):
        await self.db(AlertModel).store(alert)

    async def store_alerts_history(self, alert: AlertsHistoryModel):
        await self.db(AlertsHistoryModel).store(alert)

    async def retrieve(self, alert_id) -> AlertModel:
        query = Query().filter_by(Compare(AlertModel.alert_uuid, '=', alert_id))
        return next(iter(await self.db(AlertModel).get(query)), None)

    async def retrieve_alert_history(self, alert_id) -> AlertsHistoryModel:
        query = Query().filter_by(Compare(AlertsHistoryModel.alert_uuid, '=', alert_id))
        return next(iter(await self.db(AlertsHistoryModel).get(query)), None)

    async def retrieve_by_sensor_info(self, sensor_info, module_type) -> AlertModel:
        filter = And(And(Compare(AlertModel.sensor_info, '=', \
                str(sensor_info)), Compare(AlertModel.module_type, "=", \
                str(module_type))), Or(Compare(AlertModel.acknowledged, '=', \
                False), Compare(AlertModel.resolved, '=', False)))
        query = Query().filter_by(filter)
        return next(iter(await self.db(AlertModel).get(query)), None)

    async def update(self, alert: AlertModel):
        await self.db(AlertModel).store(alert)

    async def update_by_sensor_info(self, sensor_info, module_type, update_params):
        filter = And(And(Compare(AlertModel.sensor_info, '=', \
                str(sensor_info)), Compare(AlertModel.module_type, "=", \
                str(module_type))), Or(Compare(AlertModel.acknowledged, '=', \
                False), Compare(AlertModel.resolved, '=', False)))
        await self.db(AlertModel).update(filter, update_params)

    def _prepare_time_range(self, field, time_range: DateTimeRange):
        db_conditions = []
        if time_range and time_range.start:
            db_conditions.append(Compare(field, '>=', time_range.start))
        if time_range and time_range.end:
            db_conditions.append(Compare(field, '<=', time_range.end))
        return db_conditions

    def _prepare_filters(self, create_time_range: DateTimeRange, show_all: bool = True,
            severity: str = None, resolved: bool = None, acknowledged: bool =
            None, show_active: bool = False):
        and_conditions = [*self._prepare_time_range(AlertModel.created_time, create_time_range)]
        if show_active:
            self._prapare_filters_show_active(and_conditions)
        else:
            if not show_all:
                or_conditions = []
                or_conditions.append(Compare(AlertModel.resolved, '=', False))
                or_conditions.append(Compare(AlertModel.acknowledged, '=', False))
                and_conditions.append(Or(*or_conditions))

            if resolved is not None:
                and_conditions.append(Compare(AlertModel.resolved, '=', resolved))

            if acknowledged is not None:
                and_conditions.append(Compare(AlertModel.acknowledged, '=',
                    acknowledged))

        if severity:
            and_conditions.append(Compare(AlertModel.severity, '=', severity))
        return And(*and_conditions) if and_conditions else None

    def _prapare_filters_show_active(self, and_conditions):
        and_cond1 = []
        and_cond1.append(Compare(AlertModel.acknowledged, '=', True))
        and_cond1.append(Compare(AlertModel.resolved, '=', False))
        ack_and = And(*and_cond1)
        and_cond2 = []
        and_cond2.append(Compare(AlertModel.acknowledged, '=', False))
        and_cond2.append(Compare(AlertModel.resolved, '=', True))
        resolved_and = And(*and_cond2)
        or_cond = []
        or_cond.append(ack_and)
        or_cond.append(resolved_and)
        active_alerts_or = Or(*or_cond)
        and_conditions.append(active_alerts_or)

    async def retrieve_by_range(
            self, create_time_range: DateTimeRange, show_all: bool=True,
            severity: str=None, sort: Optional[SortBy]=None,
            limits: Optional[QueryLimits]=None, resolved: bool = None, acknowledged: bool = None,
            show_active: bool=False) -> Iterable[AlertModel]:

        query_filter = self._prepare_filters(create_time_range, show_all, severity,
                resolved, acknowledged, show_active)
        query = Query().filter_by(query_filter)

        if not limits:
            limits = QueryLimits(const.ES_RECORD_LIMIT, 0)

        if limits and limits.offset:
            query = query.offset(limits.offset)

        if limits and limits.limit:
            query = query.limit(limits.limit)

        if sort:
            query = query.order_by(getattr(AlertModel, sort.field), sort.order)
        Log.debug(f"Alerts service Retrive by range: {query_filter}")
        return await self.db(AlertModel).get(query)

    async def count_by_range(self, create_time_range: DateTimeRange, show_all: bool = True,
            severity: str = None, resolved: bool = None,
            acknowledged: bool = None, show_active: bool = False) -> int:
        Log.debug(f"Alerts service count by range: {create_time_range}")
        return await self.db(AlertModel).count(
            self._prepare_filters(create_time_range, show_all, severity, resolved,
                acknowledged, show_active))

    async def retrieve_all(self) -> list:
        """
        Retrieves all the alerts
        """
        pass

    async def retrieve_all_alerts_history(self, create_time_range: DateTimeRange, \
            sort: Optional[SortBy]=None, limits: Optional[QueryLimits]=None, \
            sensor_info: str = None) -> Iterable[AlertsHistoryModel]:

        query_filter = self._prepare_history_filters(create_time_range, sensor_info)
        query = Query().filter_by(query_filter)

        if limits and limits.offset:
            query = query.offset(limits.offset)

        if limits and limits.limit:
            query = query.limit(limits.limit)

        if sort:
            query = query.order_by(getattr(AlertsHistoryModel, sort.field), sort.order)
        Log.debug(f"Alerts service : Retrive alerts for history: {query_filter}")
        return await self.db(AlertsHistoryModel).get(query)

    async def retrieve_by_ids(self, alert_ids)-> Iterable[AlertsHistoryModel]:
        compares = list()
        for uuid in alert_ids:
            compares.append(Compare(AlertModel.alert_uuid, "=", uuid))
        filter = Or(*compares)
        query = Query().filter_by(filter)
        return await self.db(AlertModel).get(query)

    async def count_alerts_history(self, create_time_range: DateTimeRange,\
            sensor_info: str = None) -> int:
        Log.debug(f"Alerts service:  Count alerts history: {create_time_range}")
        return await self.db(AlertsHistoryModel).count(\
                self._prepare_history_filters(create_time_range, sensor_info))

    def _prepare_history_filters(self, create_time_range: DateTimeRange, \
            sensor_info: str = None):
        and_conditions = [*self._prepare_time_range\
                (AlertsHistoryModel.created_time, create_time_range)]

        if sensor_info:
            and_conditions.append(Compare(AlertsHistoryModel.sensor_info, '=', sensor_info))

        return And(*and_conditions) if and_conditions else None

    async def retrieve_unresolved_by_node_id(self, node_id) -> Iterable[AlertModel]:
        alert_filter = And(Compare(AlertModel.node_id, '=', node_id), \
            Or(Compare(AlertModel.acknowledged, '=', False), \
            Compare(AlertModel.resolved, '=', False)))
        query = Query().filter_by(alert_filter)
        limits = QueryLimits(const.ES_RECORD_LIMIT, 0)
        query = query.offset(limits.offset)
        query = query.limit(limits.limit)
        return await self.db(AlertModel).get(query)

    def set_hostname_in_alert(self, alert):
        if alert and alert.get(const.HOST_ID):
                alert[const.HOSTNAME] = self.hostname_nodeid_map.get(alert.get(const.HOST_ID),
                                                alert.get(const.HOST_ID))
        return alert

    async def fetch_alert_for_support_bundle(self):
        """
        Fetches New and Active alerts except for IEM alerts.
        Fetches alerts whose life cycle is completed(resovled + ack) for 7 days.
        1. Fetching New alerts (resolved and ack both false)
        """
        combined_alert_list = []
        new_alerts_list = await self.retrieve_by_range(
            None, #time_range
            True, #show_all
            None, #severity
            None, #SortBy
            None, #limits
            False, #resolved,
            False, #acknowledged,
            False #show_active
        )
        combined_alert_list.extend(new_alerts_list)
        """
        2. Fetching active alerts (either resolved or ack) is true.
        """
        active_alerts_list = await self.retrieve_by_range(
            None, #time_range
            True, #show_all
            None, #severity
            None, #SortBy
            None, #limits
            None, #resolved,
            None, #acknowledged,
            True  #show_active
        )
        combined_alert_list.extend(active_alerts_list)
        """
        3. Fetching alerts that have been resolved and ack both.
        This means that the alert has completed the life cycle.
        For these alerts we will only fetch the data for last 7 days.
        """
        start_time = datetime.utcnow() - timedelta(**{"days": 7})
        resolved_alerts_list = await self.retrieve_by_range(
            DateTimeRange(start_time, None), #time_range
            True, #show_all
            None, #severity
            None, #SortBy
            None, #limits
            True, #resolved,
            True, #acknowledged,
            False  #show_active
        )
        combined_alert_list.extend(resolved_alerts_list)
        return [self.set_hostname_in_alert(alert.to_primitive_filter_empty()) for alert in combined_alert_list if not alert.module_type == const.IEM]

class IemAppService(ApplicationService):
    """
    Provides producer and consumer operations on IEMs
    """
    severity_levels = {
        'INFO' : 'I',
        'WARN' : 'W',
        'ERROR' : 'E',
        'CRITICAL' : 'X',
        'ALERT' : 'A',
        'NOTICE' : 'N',
        'CONFIG' : 'C',
        'DETAIL' : 'D',
        'DEBUG' : 'B'
    }

    modules = {
        'SSL_EXPIRY': 'SSL'
    }

    def __init__(self, repo: IemRepository):
        super().__init__()
        self._repo = repo

    def init(self, source: str = 'S', component: str = 'CSM'):
        Log.info(f"Intializing IEM service - Component: {component}, Source: {source}")
        try:
            EventMessage.init(component, source)
        except EventMessageError as iemerror:
            Log.error(f"Event Message Initialization Error : {iemerror}")

    def send(self, payload: IemPayload):
        Log.info("Sending IEM : {payload}")
        try:
            # Message BLOB format is not defined yet. Using string as the data type.
            EventMessage.send(module=payload.module, event_id=payload.event_id, severity=payload.severity, \
                message_blob=payload.message_blob)
        except EventMessageError as iemerror:
            Log.error(f"Error in sending IEM. Payload : {payload}. {iemerror}")

class IemMonitorService(Service, Observable):
    """
    IEM Monitor works with Message Bus to monitor IEMs.
    When IEM Monitor receives a fetch request, it scans the DB and
    Then it waits for Message Bus to notice if there are any new IEMs.
    IEM Monitor takes action on the received IEMs using a callback.
    Actions include (1) storing on the DB and (2) sending to subscribers, i.e.
    web server.
    """
    def __init__(self, repo: IemRepository):#, http_notifications):
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self.repo = repo
        #self._http_notfications = http_notifications
        #self._es_retry = Conf.get(const.CSM_GLOBAL_INDEX, const.ES_RETRY, 5)
        super().__init__()

    def start(self):
        """
        This method creats and starts an IEM monitor thread
        """
        Log.info("Starting IEM monitor thread")
        try:
            if not self._thread_running and not self._thread_started:
                time.sleep(1.0)
                EventMessage.subscribe('Manager')
                self._thread_started = True
                self._thread_running = True
                self._iem_monitor_thread = Thread(target=self._monitor_iem,
                                              args=(self._recv,))
                self._iem_monitor_thread.start()

        except Exception as e:
            Log.warn(f"Error in starting alert monitor thread: {e}")

    def stop(self):
        try:
            Log.info("Stopping IEM monitor thread")
            self._thread_started = False
            self._thread_running = False
            self._iem_monitor_thread.join()
            Log.info("Stopped IEM monitor thread")
        except Exception as e:
            Log.warn(f"Error in stopping IEM monitor thread: {e}")

    def _recv(self, iem):
        print(iem)

    def _monitor_iem(self, callback):
        while self._thread_running:
            try:
                alert = EventMessage.receive()
                callback(alert)
                time.sleep(5.0)
            except EventException as e:
                Log.error(f"Error occured during IEM receive process. {e}")
