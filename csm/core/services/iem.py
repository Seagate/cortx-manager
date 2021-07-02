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
from typing import NamedTuple, Any
from csm.common.observer import Observable
import time
from csm.common.payload import Payload, Json, JsonMessage, Dict
from cortx.utils.log import Log
from threading import Thread
from csm.core.blogic import const
import uuid
from csm.plugins.cortx.alert import AlertSchemaValidator
from marshmallow import ValidationError

class Messageblob(NamedTuple):
    visible: bool
    description: str
    destination: str
    type: str
    recommendation: Any = ''
    extended_info: Any = {}

class IemPayload(NamedTuple):
    severity: str
    module: str
    event_id: int
    message_blob: Messageblob

class IemAppService(ApplicationService):
    """
    Provides consumer operations on IEMs
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
        """
        Intializing EventMessage for sending IEMs.
        :param source : A single character that indicates type of component.
                        i.e H-Hardware, S-Software, F-Firmware, O-OS
        :param component: Indicates component that generated IEM.
        :return: None
        """
        Log.info(f"Intializing IEM service - Component: {component}, Source: {source}")
        try:
            EventMessage.init(component, source)
        except EventMessageError as iemerror:
            Log.error(f"Event Message Initialization Error : {iemerror}")

    def send(self, payload: IemPayload):
        """
        Function to send IEMs
        :param payload : Paylod contains all the information required for IEM
        :return None
        """
        try:
            # Message BLOB format is not defined yet. Using string as the data type.
            msg_blob = dict(payload.message_blob._asdict())
            EventMessage.send(module=payload.module, event_id=payload.event_id, severity=payload.severity, \
                message_blob=msg_blob)
            Log.info(f"IEM alert sent: {payload}")
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
    def __init__(self):
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self.mapping_dict = Json(const.IEM_MAPPING_TABLE).load()
        super().__init__()

    def init(self, callback):
        """
        Initializes the callback set by Alert Monitor
        :param: callback: Callback method provided by alert monitor
        """
        self.callback = callback

    def start(self):
        """
        This method creats and starts an IEM monitor thread
        :param None
        :return None
        """
        Log.info("Starting IEM monitor thread")
        try:
            if not self._thread_running and not self._thread_started:
                EventMessage.subscribe('Manager')
                self._thread_started = True
                self._thread_running = True
                self._iem_monitor_thread = Thread(target=self._monitor_iem,
                                              args=(self._recv,))
                self._iem_monitor_thread.start()

        except Exception as e:
            Log.warn(f"Error in starting alert monitor thread: {e}")

    def stop(self):
        """
        This methos stops the IEM monitor
        :param None
        :return None
        """
        try:
            Log.info("Stopping IEM monitor thread")
            self._thread_started = False
            self._thread_running = False
            self._iem_monitor_thread.join()
            Log.info("Stopped IEM monitor thread")
        except Exception as e:
            Log.warn(f"Error in stopping IEM monitor thread: {e}")

    def _convert_schema(self, message):
        """
        Parsing the IEM message to create the csm specific schema
        After converting the message the converted message will be sent to
        alert monitor for storing and publishing it.
        :param message: The IEM message received
        """
        Log.debug(f"Converting to CSM specific schema:{message}")
        iem_schema = {}
        try:
            input_schema = Payload(Dict(message))
            # Only proceed if the IEM is targeted for end user
            if input_schema.get('iem.contents.message.visible'):
                converted_schema = Payload(Dict(dict()))
                input_schema.convert(self.mapping_dict.get(const.COMMON), \
                    converted_schema)
                converted_schema.dump()
                iem_schema = converted_schema.load()
                if self._prepare_iem_info(iem_schema):
                    self._validate_and_send(iem_schema)
        except Exception as ex:
            Log.error(f"Error occurced in converting IEM schema: {ex}")

    def _validate_and_send(self, message):
        """
        Method validates IEM Schema using marshmallow.
        :param message: IEM alert
        :return None
        """
        try:
            if self.callback:
                Log.debug(f"Validating IEM alert: {message}")
                alert_validator = AlertSchemaValidator()
                alert_data = alert_validator.load(message,  unknown='EXCLUDE')
                status = self.callback(alert_data)
                Log.info(f"IEM Alert validated and sent to alert monitor. Status: {status}")
        except ValidationError as ve:
            Log.warn(f"IEM Validation error: {ve}")
        except Exception as e:
            Log.warn(f"Error occured during processing IEM alerts: {e}")

    def _prepare_iem_info(self, iem_schema):
        """
        This method converts the IEM alert from any module to CSM specific schema.
        Currently HW/SW input schema is different than IEM schema. So, the IEM
        schema needs to be mapped differently so that it complies with CSM alert schema.
        :param iem_schema: IEM input schema
        :return True/False
        """
        ret_value = False
        try:
            iem_schema[const.ALERT_UUID] = f"{int(time.time())}{uuid.uuid4()}"
            component = iem_schema[const.ALERT_SENSOR_INFO][const.COMPONENT_ID]
            module = iem_schema[const.ALERT_SENSOR_INFO][const.MODULE_ID]
            iem_schema[const.ALERT_NODE_ID] = iem_schema[const.ALERT_SENSOR_INFO][const.ALERT_NODE_ID]
            iem_schema[const.ALERT_MODULE_NAME] = f"node:iem:{component}:{module}"
            iem_schema[const.ALERT_MODULE_TYPE] = f"{module}"
            iem_schema[const.ALERT_RESOURCE_ID] = f"{component}:{module}"
            iem_schema[const.ALERT_CREATED_TIME] = \
                int(iem_schema[const.ALERT_CREATED_TIME])
            iem_schema[const.ALERT_UPDATED_TIME] = int(time.time())
            iem_schema[const.ALERT_RESOLVED] = False
            iem_schema[const.ALERT_ACKNOWLEDGED] = False
            iem_schema[const.ALERT_COMMENT] = ""
            iem_schema[const.SUPPORT_MESSAGE] = ""
            obj_extended_info = JsonMessage(iem_schema[const.ALERT_EXTENDED_INFO])
            extended_info = iem_schema[const.ALERT_EXTENDED_INFO]
            if not extended_info[const.SPECIFIC_INFO]:
                extended_info[const.SPECIFIC_INFO] = {}
            if not iem_schema[const.HOST_ID]:
                iem_schema[const.HOST_ID] = ''
            info = extended_info[const.ALERT_INFO]
            if info:
                info[const.DESCRIPTION] = iem_schema[const.DESCRIPTION]
                info[const.ALERT_RESOURCE_ID] = iem_schema[const.ALERT_RESOURCE_ID]
                info[const.ALERT_RESOURCE_TYPE] = iem_schema[const.ALERT_MODULE_NAME]
                info[const.ALERT_EVENT_TIME] = iem_schema[const.CREATED_TIME]
            iem_schema[const.ALERT_SENSOR_INFO] = \
                '_'.join(str(x) for x in iem_schema[const.ALERT_SENSOR_INFO].values())
            iem_schema[const.ALERT_SENSOR_INFO] = \
                iem_schema[const.ALERT_SENSOR_INFO].replace(" ", "_")
            iem_schema[const.ALERT_EXTENDED_INFO] = obj_extended_info.dump(iem_schema[const.ALERT_EXTENDED_INFO])
            ret_value = True
        except Exception as ex:
            Log.error(f"Error occurced in parsing IEM schema: {ex}")
        return ret_value


    def _recv(self, message):
        """
        This a callback method where the IEM messages will be sent once
        received from IEM monitor.
        :param message: IEM message received from communication channel
        :return None
        """
        if message:
            Log.info(f"IEM Message : {message}")
            self._convert_schema(message)

    def _monitor_iem(self, callback):
        """
        The is a thread function and it will keep on polling for IEM alerts
        every 1 second.
        :param callback: Callback function where IEM message will be send.
        :return None
        """
        while self._thread_running:
            try:
                alert = EventMessage.receive()
                callback(alert)
                time.sleep(1.0)
            except EventException as e:
                Log.error(f"Error occured during IEM receive process. {e}")
