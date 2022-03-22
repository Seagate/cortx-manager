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

# Let it all reside in a separate controller until we've all agreed on request
# processing architecture
import re
import time
from csm.common.observer import Observable
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from cortx.utils.log import Log
from csm.common.email import EmailSender
from csm.common.services import Service, ApplicationService
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from csm.core.blogic.models.alerts import IAlertStorage, Alert
from csm.common.errors import CsmNotFoundError, CsmError, InvalidRequest
from csm.core.blogic import const
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from cortx.utils.data.access.filters import Compare, And, Or
from cortx.utils.data.access import Query, SortOrder
from csm.core.blogic.models.alerts import AlertModel, AlertsHistoryModel
from csm.core.blogic.models.comments import CommentModel
from csm.core.services.system_config import SystemConfigManager
from csm.core.services.users import UserManager
from csm.common import queries
from schematics import Model
from schematics.types import StringType, BooleanType, IntType
from typing import Optional, Iterable, Dict
from csm.common.payload import Payload, Json, JsonMessage
import asyncio
from cortx.utils.conf_store.conf_store import Conf


ALERTS_MSG_INVALID_DURATION = "alert_invalid_duration"
ALERTS_MSG_NOT_FOUND = "alerts_not_found"
ALERTS_MSG_NOT_RESOLVED = "alerts_not_resolved"
ALERTS_MSG_TOO_LONG_COMMENT = "alerts_too_long_comment"
ALERTS_MSG_RESOLVED_AND_ACKED_ERROR = "alerts_resolved_and_acked"
ALERTS_MSG_NON_SORTABLE_COLUMN = "alerts_non_sortable_column"

class AlertRepository(IAlertStorage):
    def __init__(self, storage: DataBaseProvider):
        self.db = storage
        self.hostname_nodeid_map = Conf.get(const.CSM_GLOBAL_INDEX, const.MAINTENANCE)

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
        Log.debug(f"Alerts update service. alert_id:{alert_id}, fields:{fields}")

        alert = await self.repo.retrieve(alert_id)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)

        if alert.resolved and alert.acknowledged:
            raise InvalidRequest(
                "The alert is both resolved and acknowledged, it cannot be modified",
                ALERTS_MSG_RESOLVED_AND_ACKED_ERROR)

        if "acknowledged" in fields:
            alert.acknowledged = AlertModel.acknowledged.to_native(fields["acknowledged"])
            alert.updated_time = int(time.time())
            """
            We will mark IEM alert as resolved as soon as it is acknowledged, as
            there will be no state change occurs for IEM alerts.
            """
            if alert.module_type == const.IEM:
                alert.resolved = AlertModel.resolved.to_native(True)

        await self.repo.update(alert)
        return self.repo.set_hostname_in_alert(alert.to_primitive())

    @Log.trace_method(Log.DEBUG)
    async def add_comment_to_alert(self, alert_uuid: str, user_id: str, comment_text: str):
        """
        Add comment to alert having alert_uuid. The comment will be saved along with alert_uuid
        :param str alert_uuid: id of alert to which comment has to be added.
        :param str user_id: user_id of the user who commented.
        :param str comment_text: actual comment text
        :returns: Comment object or None
        """
        alert = await self.repo.retrieve(alert_uuid)
        if not alert:
            raise CsmNotFoundError(f"Alert not found for id {alert_uuid}", ALERTS_MSG_NOT_FOUND)

        if alert.resolved and alert.acknowledged:
            raise InvalidRequest(
                "The alert is both resolved and acknowledged, it cannot be modified",
                ALERTS_MSG_RESOLVED_AND_ACKED_ERROR)

        if alert["comments"] is None:
            alert["comments"] = []
        alert[const.ALERT_UPDATED_TIME] = int(time.time())
        alert_comment = self.build_alert_comment_model(str(len(alert["comments"]) + 1), comment_text, user_id)
        alert["comments"].append(alert_comment)
        await self.repo.update(alert)

        return alert_comment.to_primitive()

    @Log.trace_method(Log.DEBUG)
    def build_alert_comment_model(self, comment_id: str, comment_text: str, created_by: str):
        """
        Build and return CommentModel object.
        :param str comment_id: id of alert comment.
        :param str created_by: user_id of the user who commented.
        :param str comment_text: actual comment text
        :returns: Comment object or None
        """
        comment = CommentModel()
        comment.comment_id = comment_id
        comment.comment_text = comment_text
        comment.created_by = created_by
        comment.created_time = datetime.now(timezone.utc)
        return comment

    @Log.trace_method(Log.DEBUG)
    async def fetch_comments_for_alert(self, alert_uuid: str):
        """
        Fetch all the comments of the alert with alert_uuid
        :param str alert_uuid: id of the alert whose comments are to be fetched.
        :returns: Comment object or None
        """
        alert = await self.repo.retrieve(alert_uuid)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)

        if alert.comments is None:
            alert.comments = []

        return {
            "comments": [comment.to_primitive() for comment in alert.comments]
        }

    async def update_all_alerts(self, fields: dict):
        """
        Update the Data of Specific Alerts
        :param fields: A dictionary containing alert ids.
                It will acknowledge all the alerts of the specified ids.
        :return:
        """
        Log.debug(f"Update all alerts service. fields:{fields}")
        if not isinstance(fields, list):
            raise InvalidRequest("Acknowledged value must be of type boolean.")

        alerts = []

        for alert_id in fields:
            alert = await self.repo.retrieve(alert_id)
            if not alert:
                raise CsmNotFoundError("Alert not found for id" + alert_id, ALERTS_MSG_NOT_FOUND)

            alert.acknowledged = AlertModel.acknowledged.to_native(True)
            alert.updated_time = int(time.time())
            """
            We will mark IEM alert as resolved as soon as it is acknowledged, as
            there will be no state change occurs for IEM alerts.
            """
            if alert.module_type == const.IEM:
                alert.resolved = AlertModel.resolved.to_native(True)
            await self.repo.update(alert)
            alerts.append(self.repo.set_hostname_in_alert(alert.to_primitive()))

        return alerts

    async def fetch_all_alerts(self, duration, direction, sort_by, severity: Optional[str] = None,
                               offset: Optional[int] = None, show_all: Optional[bool] = True,
                               page_limit: Optional[int] = None, resolved: bool =
                               None, acknowledged: bool = None, show_active: Optional[bool] = False) -> Dict:
        """
        Fetch All Alerts
        :param duration: time duration for range of alerts
        :param direction: direction of sorting asc/desc
        :param severity: if passed, alerts will be filtered by the passed severity
        :param sort_by: key by which sorting needs to be performed.
        :param offset: offset page (1-based indexing)
        :param page_limit: no of records to be displayed on a page.
        :param resolved: alerts filtered by resolved status when show_all is true.
        :param acknowledged: alerts filtered by acknowledged status when
        show_all is true.
        :param show_active: active alerts will fetched. Active alerts are
        identified as only one flag out of acknowledged and resolved flags
        must be true and the other must be false.
        :return: :type:list
        """
        time_range = None
        Log.debug(f"Fetch all alerts service. duration:{duration}, direction:{direction}, "
                  f"sort_by:{sort_by}, severity:{severity}, offset:{offset}")
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
            raise InvalidRequest("The specified column cannot be used for sorting",
                ALERTS_MSG_NON_SORTABLE_COLUMN)

        limits = None
        if offset is not None and offset > 1:
            limits = QueryLimits(page_limit, (offset - 1) * page_limit)
        elif page_limit is not None:
            limits = QueryLimits(page_limit, 0)

        # TODO: the function takes too many parameters
        alerts_list = await self.repo.retrieve_by_range(
            time_range,
            show_all,
            severity,
            SortBy(sort_by, SortOrder.ASC if direction == "asc" else SortOrder.DESC),
            limits,
            resolved,
            acknowledged,
            show_active
        )

        alerts_count = await self.repo.count_by_range(time_range, show_all,
                severity, resolved, acknowledged, show_active)
        return {
            "total_records": alerts_count,
            "alerts": [self.repo.set_hostname_in_alert(alert.to_primitive_filter_empty()) for alert in alerts_list]
        }

    async def fetch_alert(self, alert_id):
        """
        Fetch a single alert by its key
        :param str alert_id: A unique identifier of the requried alert
        :returns: Alert object or None
        """
        Log.debug(f"Fetch alerts service alert_id:{alert_id}" )
        # This method is for debugging purposes only
        alert = await self.repo.retrieve(alert_id)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)
        return self.repo.set_hostname_in_alert(alert.to_primitive_filter_empty())

    async def fetch_all_alerts_history(self, duration, direction, sort_by, \
                                        offset: Optional[int] = None \
                                        , page_limit: Optional[int] = None, \
                                        sensor_info: Optional[str] = None, \
                                        start_date = None, end_date = None) -> Dict:
        """
        Fetch All Alerts to show history
        :param duration: time duration for range of alerts
        :param direction: direction of sorting asc/desc
        :param sort_by: key by which sorting needs to be performed.
        :param offset: offset page (1-based indexing)
        :param page_limit: no of records to be displayed on a page.
        :return: :type:list
        """
        time_range = None
        Log.debug(f"Fetch alerts to show history. duration:{duration}, direction:{direction}, "
                  f"sort_by:{sort_by}, offset:{offset}")
        if duration:  # Filter
            # TODO: time format can generally be API-dependent. Better pass here an
            # already parsed TimeDelta object.
            time_duration = int(re.split(r'[a-z]', duration)[0])
            time_format = re.split(r'[0-9]', duration)[-1]
            dur = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            start_time = (datetime.utcnow() - timedelta(
                **{dur[time_format]: time_duration}))
            time_range = DateTimeRange(start_time, None)

        if start_date and end_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            time_range = DateTimeRange(start_datetime, end_datetime)

        if sort_by and sort_by not in const.ALERT_SORTABLE_FIELDS:
            raise InvalidRequest("The specified column cannot be used for sorting",
                ALERTS_MSG_NON_SORTABLE_COLUMN)

        limits = None
        if offset is not None and offset > 1:
            limits = QueryLimits(page_limit, (offset - 1) * page_limit)
        elif page_limit is not None:
            limits = QueryLimits(page_limit, 0)

        alerts_list = await self.repo.retrieve_all_alerts_history(
            time_range,
            SortBy(sort_by, SortOrder.ASC if direction == "asc" else SortOrder.DESC),
            limits,
            sensor_info
        )

        alerts_count = await self.repo.count_alerts_history(time_range, sensor_info)
        return {
            "total_records": alerts_count,
            "alerts": [self.repo.set_hostname_in_alert(alert.to_primitive_filter_empty()) for alert in alerts_list]
        }

    async def fetch_alert_history(self, alert_id):
        """
        Fetch a single alert by its key
        :param str alert_id: A unique identifier of the requried alert
        :returns: Alert object or None
        """
        Log.debug(f"Fetch alerts history by id. alert_id:{alert_id}" )
        alert = await self.repo.retrieve_alert_history(alert_id)
        if not alert:
            raise CsmNotFoundError("Alert was not found", ALERTS_MSG_NOT_FOUND)
        return self.repo.set_hostname_in_alert(alert.to_primitive_filter_empty())

class AlertEmailNotifier(Service):
    def __init__(self, email_sender_queue, config_manager: SystemConfigManager,
                 template, user_manager: UserManager):
        super().__init__()
        self.email_sender_queue = email_sender_queue
        self.config_manager = config_manager
        self.template = template
        self.user_manager = user_manager

    @Log.trace_method(Log.DEBUG)
    async def handle_alert(self, alert):
        # TODO: check if email notification is enabled for alerts
        system_config = await self.config_manager.get_current_config()

        if not system_config:
            return

        email_config = system_config.notifications.email

        if not email_config:
            return  # Nothing to do

        smtp_config = email_config.to_smtp_config()
        """
        Getting the values from alert for filling in email template
        """
        extended_info = JsonMessage(alert.get(const.ALERT_EXTENDED_INFO)).load()
        info = extended_info.get(const.ALERT_INFO)
        alert_template_params = {
            'resource_id': info.get(const.ALERT_RESOURCE_ID, ""),
            'module_type': alert.get(const.ALERT_MODULE_TYPE, ""),
            'cluster_id': info.get(const.ALERT_CLUSTER_ID, ""),
            'site_id': info.get(const.ALERT_SITE_ID, ""),
            'rack_id': info.get(const.ALERT_RACK_ID, ""),
            'node_id': info.get(const.ALERT_NODE_ID, ""),
            'resource_type': info.get(const.ALERT_RESOURCE_TYPE, ""),
            'state': alert.get(const.ALERT_STATE, ""),
            'resolved': alert.get(const.ALERT_RESOLVED, ""),
            'acknowledged': alert.get(const.ALERT_ACKNOWLEDGED, ""),
            'description': alert.get(const.DESCRIPTION, ""),
            'created_on': alert.created_time.strftime(const.CSM_ALERT_NOTIFICATION_TIME_FORMAT),
            'updated_on': alert.updated_time.strftime(const.CSM_ALERT_NOTIFICATION_TIME_FORMAT)
        }
        html_body = self.template.render(**alert_template_params)
        subject = const.CSM_ALERT_EMAIL_NOTIFICATION_SUBJECT
        message = EmailSender.make_multipart(email_config.smtp_sender_email,
            None, subject, html_body)
        email_list = await self.user_manager.get_list_alert_notification_emails()
        target_emails = email_config.get_target_emails()
        target_emails.extend(email_list)

        Log.debug(f"Fetch target email  {target_emails}")
        await self.email_sender_queue.enqueue_bulk_email(message,
            target_emails, smtp_config)

class AlertMonitorService(Service, Observable):
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

    def __init__(self, repo: AlertRepository, plugin, http_notifications):
        """
        Initializes the Alert Plugin
        """
        self._alert_plugin = plugin
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._ret = False
        self.repo = repo
        self._http_notfications = http_notifications
        self._es_retry = Conf.get(const.CSM_GLOBAL_INDEX, const.ES_RETRY, 5)
        super().__init__()

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
        Log.info("Starting Alert monitor thread")
        try:
            if not self._thread_running and not self._thread_started:
                self._monitor_thread = Thread(target=self._monitor,
                                              args=())
                self._monitor_thread.start()
                self._thread_started = True
        except Exception as e:
            Log.warn(f"Error in starting alert monitor thread: {e}")

    def stop(self):
        try:
            Log.info("Stopping Alert monitor thread")
            self._alert_plugin.stop()
            Log.info("Joining Alert monitor thread")
            self._monitor_thread.join(timeout=2.0)

            self._thread_started = False
            self._thread_running = False
            Log.info("Stopped Alert monitor thread")
        except Exception as e:
            Log.warn(f"Error in stopping alert monitor thread: {e}")

    def _get_previous_alert(self, sensor_info, module_type):
        """
        This method fetches the prev alert. Before saving the alert into
        ES DB we get the previous state of the alert.
        During fault on the private network ES might take some time to clone
        the data. During this duration if an alert comes CSM wont be able to
        save it in ES and alert will be lost.
        So, to handle this corner case when an exception comes we will sleep for
        5 seconds and then will retry the ES connection.
        Even if more then one alert piles up on RMQ queue this fix will handle it.
        """
        prev_alert = None
        for count in range(0, int(self._es_retry)):
            try:
                Log.info("Fetching previous alert to check the state and severity.")
                prev_alert = self._run_coroutine\
                    (self.repo.retrieve_by_sensor_info(sensor_info, module_type))
                return prev_alert
            except Exception as ex:
                Log.warn(f"Unable to fetch previous alert. Retrying : {count+1}.{ex}")
                time.sleep(2**count)
                continue

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
        """ After saving/ updating alert, update the in memory health schema """
        try:
            Log.debug(f"Incoming alert: {message}")
            for key in [const.ALERT_CREATED_TIME, const.ALERT_UPDATED_TIME]:
                message[key] = datetime.utcfromtimestamp(message[key])\
                        .replace(tzinfo=timezone.utc)
            sensor_info = message.get(const.ALERT_SENSOR_INFO, "")
            module_type = message.get(const.ALERT_MODULE_TYPE, "")
            is_node_alert = self._is_node_alert(message[const.ALERT_MODULE_NAME])
            is_high_risk_severity = self._is_high_risk_severity(\
                message[const.ALERT_SEVERITY])
            """
            Checking for node hw alert.
            If the alert is node hw alert and severity is in the category of
            high risk, then we will prepend the description field with support message.
            """
            if is_node_alert and is_high_risk_severity:
                self._add_support_message(message)
            prev_alert = self._get_previous_alert(sensor_info, module_type)
            alert = AlertModel(message)
            self.update_bad_alert_flag=False
            if not prev_alert:
                """
                Checking if the new alert is good or not. If it is good then
                we need to set the resolved flag.
                """
                if self._is_good_alert(alert):
                    alert.resolved = True
                self._run_coroutine(self.repo.store(alert))
                self.add_listener(self._http_notfications.handle_alert)
                Log.debug(f"Alert stored successfully. Alert ID : {alert.alert_uuid}")
            else:
                if self._resolve_alert(message, prev_alert):
                    self.remove_listener(self._http_notfications.handle_alert)
                    alert.alert_uuid = prev_alert.alert_uuid
                    Log.debug(f"Alert updated successfully." \
                            f"Alert ID : {alert.alert_uuid}")
            self._notify_listeners(alert, loop=self._loop)
            """
            Storing the incoming alert to alert's history collection.
            These alerts will be shown on UI in a seperate alert's history tab.
            """
            alert_history = AlertsHistoryModel(message)
            self._run_coroutine(self.repo.store_alerts_history(alert_history))
        except Exception as e:
            Log.warn(f"Error in consuming alert: {e}")
            return False

        return True

    def _resolve_alert(self, new_alert, prev_alert):
        alert_updated = False
        if not self._is_duplicate_alert(new_alert, prev_alert):
            if self._is_good_alert(new_alert):
                """
                If it is a good alert checking the state of previous alert.
                """
                if self._is_good_alert(prev_alert):
                    """ Previous alert is a good one so updating. """
                    self._update_alert(new_alert, prev_alert)
                else:
                    """ Previous alert is a bad one so resolving it. """
                    self._resolve(new_alert, prev_alert)
                alert_updated = True
            if self._is_bad_alert(new_alert):
                """
                If it is a bad alert checking the state of previous alert.
                """
                self.update_bad_alert_flag = True
                if self._is_bad_alert(prev_alert):
                    """ Previous alert is a bad one so updating. """
                    self._update_alert(new_alert, prev_alert)
                else:
                    """
                    Previous alert is a good one so updating and marking the
                    resolved status to False.
                    """
                    self._update_alert(new_alert, prev_alert, True)
                alert_updated = True
        else:
            self._update_duplicate_alert(new_alert, prev_alert)
        return alert_updated

    def _is_duplicate_alert(self, new_alert, prev_alert):
        """
        Check whether the alerts is duplicate or not based on state.
        :param alert : New Alert Dict
        :param prev_alert : Previous Alert object
        :return: boolean (True or False)
        """
        ret = False
        if new_alert.get(const.ALERT_STATE, "") == prev_alert.state:
            ret = True
        return ret

    def _update_alert(self, alert, prev_alert, update_resolve=False):
        """
        Update the alerts to storage.
        :param alert : Alert object
        :param prev_alert : Previous Alert object
        :param update_resolve : If set to True, we will mark resolved state to
        False
        :return: None
        """
        update_params = {}
        is_node_alert = self._is_node_alert(alert.get(const.ALERT_MODULE_NAME))
        is_high_risk_severity = self._is_high_risk_severity(\
            alert.get(const.ALERT_SEVERITY))
        """
        Updating the support message based on severity for node related alerts.
        During updation the severity might get changed from high risk to low.
        """
        if is_node_alert and is_high_risk_severity:
            update_params[const.SUPPORT_MESSAGE] = alert.get(const.SUPPORT_MESSAGE)
        else:
            update_params[const.SUPPORT_MESSAGE] = ''
        if update_resolve:
            update_params[const.ALERT_RESOLVED] = alert.get(const.ALERT_RESOLVED, "")
        else:
            update_params[const.ALERT_RESOLVED] = prev_alert.resolved
        update_params[const.ALERT_STATE] = alert.get(const.ALERT_STATE, "")
        update_params[const.ALERT_SEVERITY] = alert.get(const.ALERT_SEVERITY, "")
        update_params[const.ALERT_UPDATED_TIME] = int(time.time())
        update_params[const.ALERT_HEALTH] = alert.get(const.ALERT_HEALTH, "")
        if self.update_bad_alert_flag:
            update_params[const.DESCRIPTION] = alert.get(const.DESCRIPTION, "")
        if alert.get(const.ALERT_MODULE_TYPE, "") == const.IEM:
            update_params[const.ALERT_CREATED_TIME] = \
                alert.get(const.ALERT_CREATED_TIME, "")
            update_params[const.DESCRIPTION] = alert.get(const.DESCRIPTION, "")
        self._update_params_cleanup(update_params)
        self._run_coroutine(self.repo.update_by_sensor_info\
                (prev_alert.sensor_info, prev_alert.module_type, update_params))

    def _update_params_cleanup(self, update_params):
        for key, value in update_params.items():
            if value is None:
                update_params[key] = ''

    def _is_good_alert(self, alert):
        """
        Check whether the alert is good or not.
        :param alert : Alert object
        :return: boolean (True or False)
        """
        ret = False
        if alert.get(const.ALERT_STATE, "") in const.GOOD_ALERT:
            ret = True
        return ret

    def _is_bad_alert(self, alert):
        """
        Check whether the alert is bad or not.
        :param alert : Alert object
        :return: boolean (True or False)
        """
        ret = False
        if alert.get(const.ALERT_STATE, "") in const.BAD_ALERT:
            ret = True
        return ret

    def _resolve(self, alert, prev_alert):
        """
        Get the previous alert with the same alert_uuid.
        :param alert: Alert Object.
        :return: None
        """
        if not prev_alert.resolved:
            """
            Try to resolve the alert if the previous alert is bad and
            the current alert is good.
            """
            prev_alert.resolved = True
            self._update_alert(alert, prev_alert)

    def _update_duplicate_alert(self, new_alert, prev_alert):
        """
        If we found that the incoming alert is duplicate, then we will
        replace the old alert stroed in ES db with the new one.
        But we will not replace the CSM specific fields like resolved,
        acknowledged and comments as the previous alert might contain
        some modified values which will be overwritten by the new one.
        """
        try:
            alert = AlertModel(new_alert)
            alert.alert_uuid = prev_alert.alert_uuid
            alert.resolved = prev_alert.resolved
            alert.acknowledged = prev_alert.acknowledged
            alert.comments = prev_alert.comments
            alert.updated_time = int(time.time())
            self._run_coroutine(self.repo.update(alert))
        except Exception as ex:
            Log.error(f"Updation of duplicate alert failed. Alert: {new_alert}")

    def _is_node_alert(self, resource_type):
        """
        This function checks whether the incoming alert is for node hw or not.
        """
        self._ret = False
        if resource_type.split(':')[0] == const.NODE:
            self._ret = True
        return self._ret

    def _add_support_message(self, alert):
        try:
            """
            Adding support message if alert is bad.
            """
            if self._is_bad_alert(AlertModel(alert)):
                texts = Json(const.L18N_SCHEMA).load()
                alert[const.SUPPORT_MESSAGE] = texts.get(const.SUPPORT_MSG, const.SUPPORT_DEFAULT_MSG)
        except Exception as ex:
            Log.error(f"Addition of support message failed. {ex}")

    def _is_high_risk_severity(self, severity):
        """
        This function checks whether the severity is of hish risk or not.
        """
        self._ret = False
        if severity in const.HIGH_RISK_SEVERITY:
            self._ret = True
        return self._ret
