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

class IemPayload(NamedTuple):
    severity: str
    module: str
    event_id: int
    message_blob: str

class IemRepository(IAlertStorage):
    def __init__(self, storage: DataBaseProvider):
        self._db = storage

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

    def __init__(self):
        super().__init__()

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
    def __init__(self, repo: IemRepository, http_notifications):
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self.repo = repo
        self._http_notfications = http_notifications
        self._es_retry = Conf.get(const.CSM_GLOBAL_INDEX, const.ES_RETRY, 5)
        EventMessage.subscribe('Manager')
        super().__init__()

    def start(self):
        """
        This method creats and starts an IEM monitor thread
        """
        Log.info("Starting IEM monitor thread")
        try:
            if not self._thread_running and not self._thread_started:
                self._iem_monitor_thread = Thread(target=self._monitor_iem,
                                              args=(), daemon=True)
                self._iem_monitor_thread.start()
                self._thread_started = True
                self._thread_running = True
        except Exception as e:
            Log.warn(f"Error in starting alert monitor thread: {e}")

    def stop(self):
        try:
            Log.info("Stopping IEM monitor thread")
            self._thread_started = False
            self._thread_running = False
            #self._monitor_thread.join()
            Log.info("Stopped IEM monitor thread")
        except Exception as e:
            Log.warn(f"Error in stopping IEM monitor thread: {e}")

    def _monitor_iem(self):
        """
        This method acts as a thread function.
        It will monitor the message bus for IEMs.
        """
        while self._thread_running:
            while true:
                try: 
                    alert = EventMessage.receive()
                    #Process the alert
                    print(alert)
                    time.sleep(2)
                except EventException as e:
			Log.error(f"Error occured during IEM receive process. {e}")
