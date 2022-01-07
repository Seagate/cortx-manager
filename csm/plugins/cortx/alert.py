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

import json
import os
import time
import asyncio
from csm.common.comm import MessageBusComm
from csm.common.errors import CsmError
from cortx.utils.log import Log
from csm.common.payload import Payload, Json, JsonMessage, Dict
from csm.common.plugin import CsmPlugin
from csm.core.blogic import const
from marshmallow import Schema, fields, ValidationError
from concurrent.futures import ThreadPoolExecutor
from csm.common.services import Service
from cortx.utils.conf_store.conf_store import Conf
try:
    from cortx.utils.ha.dm.decision_maker import DecisionMaker
except ModuleNotFoundError:
    Log.warn("Unable to import HA Decision Maker Library.")
    DecisionMaker = None

class AlertSchemaValidator(Schema):
    """
    AlertSchemaValidator for validating the schema using marshmallow for AlertPlugin.
    """
    alert_uuid = fields.String(required=True,
                               description="uuid to identify an  alert.")
    sensor_info = fields.String(required=True,
                                description="unique key to identify hardware."
                                            "Combination of site_id,node_id,rack_id,"
                                            "resource_id,cluster_id")
    state = fields.String(required=True,
                          description="State of the alert "
                                      "(e.g. missing| insertion etc.)")
    created_time = fields.Integer(required=True,
                                  description="Origination time of the alert")
    updated_time = fields.Integer(required=False,
                                  description="Updation time of the alert")
    resolved = fields.Boolean(required=False,
                              description="Resolution status of an alert."
                                          " (e.g. True | False)")
    acknowledged = fields.Boolean(required=False,
                                  description="Alert is acknowldeged by the user or not."
                                              "(e.g. True | False)")
    severity = fields.String(required=True,
                             description="Severity of an alert.(e.g. TBD")
    module_type = fields.String(required=False,
                                description="Type of the module. (e.g. PSU, FAN)")
    module_name = fields.String(required=False,
                                description="Name of the module. (e.g. Fan Module 4)")
    description = fields.String(required=False, allow_none=True,
                                description="This is the id from which a "
                                            "description will be fetched (e.g. TBD)")
    health = fields.String(required=False, allow_none=True,
                           description="Describes the health of PSU, \
                                   Controller, Disk etc.")
    health_recommendation = fields.String(required=False, allow_none=True,
                                          description="This is the health \
                                                  recommendation string.")
    extended_info = fields.String(required=False, description="Extended Info")
    event_details = fields.String(required = False, \
            description = "Specific fields to display.")
    name = fields.String(required = False, allow_none = True, description = \
            "Name for specific modules.")
    serial_number = fields.String(required = False, allow_none = True, \
            description = "Serial number of the resource.")
    volume_group = fields.String(required = False, allow_none = True, \
                        description = "Disk volume group.")
    volume_size = fields.String(required = False, allow_none = True, \
                        description = "Disk size.")
    volume_total_size = fields.String(required = False, allow_none = True, \
                        description = "Disk total size.")
    version = fields.String(required = False, allow_none = True, \
                        description = "Version information for resources.")
    location = fields.String(required = False, allow_none = True, \
                        description = "Location of the resources.")
    disk_slot = fields.Integer(required=False, allow_none = True, \
            description="Slot number of the disk.")
    durable_id = fields.String(required=False, description="Durable Id")
    host_id = fields.String(required=True, description="Host id of the resource")
    source = fields.String(required=False, description="Source for IEM")
    component = fields.String(required=False, description="Component for IEM")
    module = fields.String(required=False, description="Module for IEM")
    node_id = fields.String(required=True, description="Node id of the resource")
    support_message = fields.String(required=False, description="Support message for alert.")
    resource_id = fields.String(required=True, description="Id of the resource")

class AlertPlugin(CsmPlugin):
    """
    Alert Plugin is responsible for listening on the comm channel and receive
    alerts. It has a callback which is called to send the received alerts. 
    Note, Alert Plugin needs to be called in thread context as it blocks while
    listening for the alerts.
    """

    def __init__(self):
        super().__init__()
        try:
            self.comm_client = MessageBusComm(Conf.get(const.CONSUMER_INDEX, const.KAFKA_ENDPOINTS))
            self.monitor_callback = None
            self.mapping_dict = Json(const.ALERT_MAPPING_TABLE).load()
            self.decision_maker_service = DecisionMakerService()
            self._consumer_id = Conf.get(const.CSM_GLOBAL_INDEX, \
                    const.CONSUMER_ID_KEY)
            self._consumer_group = Conf.get(const.CSM_GLOBAL_INDEX, \
                    const.CONSUMER_GROUP_KEY)
            self._consumer_message_types = Conf.get(const.CSM_GLOBAL_INDEX, \
                    const.CONSUER_MSG_TYPES_KEY)
            self._offset = Conf.get(const.CSM_GLOBAL_INDEX, \
                    const.CONSUMER_OFFSET)
        except Exception as e:
            Log.exception(e)

    def init(self, callback_fn):
        """
        Establish connection with the RMQ Server.
        AlertPlugin's _listen method acts as the thread function.
        Parameters -
        1. callback_fn :- This parameter specifies the name AlertMonitor 
           class function to which plugin will send the alerts as JSON string.  
        """
        try:
            self.monitor_callback = callback_fn
            self.comm_client.init(type=const.CONSUMER, consumer_id=self._consumer_id, \
                    consumer_group=self._consumer_group, \
                    consumer_message_types=self._consumer_message_types, \
                    auto_ack=False, offset=self._offset)
        except Exception as e:
            Log.error(f"Error occured while calling alert plugin init. {e}")

    def process_request(self, **kwargs):
        for key, value in kwargs.items():
            if key == const.CSM_ALERT_CMD and value.strip() == 'listen':
                self._listen()

    def _plugin_callback(self, message):
        """
        1. This is the callback method on which we will receive the 
           alerts from Comm class.
        2. This method will call AlertMonitor class function and will 
           send the alert JSON string as parameter.
        3. Upon receiving the status(i.e True) we will then acknowledge the
           alert.
        Parameters -
        1. body - Actual alert JSON string
        Validations performed:
        1. Validated without resource-type
        2. Validating with wrong resource type as per mapping dict.
        3. Validating with wrong data type in schema.
        4. Validating empty alert data.
        5. Validating with all appropriate data.
        Since actuator response and alerts comes on same channel we need to
        bifercate them.
        """
        status = False
        sensor_queue_msg = None
        try:
            sensor_queue_msg = JsonMessage(message).load()
        except ValueError as ex:
            Log.error(f"Alert message parsing failed. {ex}")
        if sensor_queue_msg:
            Log.info(f"Message on sensor queue: {sensor_queue_msg}")
            title = sensor_queue_msg.get("title", "")
            if "sensor" in title.lower():
                try:
                    if self.monitor_callback:
                        Log.info("Coverting and validating alert.")
                        alert = self._convert_to_csm_schema(message)
                        """Validating Schema using marshmallow"""
                        alert_validator = AlertSchemaValidator()
                        alert_data = alert_validator.load(alert,  unknown='EXCLUDE')
                        Log.debug(f"Alert validated : {alert_data}")
                        status = self.monitor_callback(alert_data)
                        """
                        Calling HA Decision Maker for Alerts.
                        """
                        if self.decision_maker_service and status:
                            self.decision_maker_service.decision_maker_callback(sensor_queue_msg)
                except ValidationError as ve:
                    # Acknowledge incase of validation error.
                    Log.warn(f"Acknowledge incase of validation error {ve}")
                    self.comm_client.acknowledge()
                except Exception as e:
                    # Code should not reach here.
                    Log.warn(f"Error occured during processing alerts: {e}")
            if status:
                # Acknowledge the alert so that it could be
                # removed from the queue.
                Log.debug(f"Marking sensor response as acknowleged. status: {status}")
                self.comm_client.acknowledge()

    def _listen(self):
        """
        This is thread function.
        This method registers the callback with basic_consume method 
        and starts consuming the alerts.
        """
        try:
            self.comm_client.recv(self._plugin_callback)
        except Exception as e:
            Log.warn(e)

    def stop(self):
        """
        This method will call comm's stop to stop consuming from the queue.
        """
        Log.info("Start: AlertPlugin's stop")
        self.comm_client.stop()
        Log.info("End: AlertPlugin's stop")

    def _convert_to_csm_schema(self, message):
        """
        Parsing the alert JSON to create the csm schema
        """
        Log.debug(f"Convert to csm schema:{message}")
        csm_schema = {}
        try:
            json_msg_obj = JsonMessage(message)
            msg_body = json_msg_obj.load()
            sub_body = msg_body.get(const.ALERT_MESSAGE, {}).get(
                const.ALERT_SENSOR_TYPE, {})
            resource_type = sub_body.get("info", {}).get\
                    (const.ALERT_RESOURCE_TYPE, "")
            if resource_type:
                res_split = resource_type.split(':')
                """
                Here resource type can be of following forms -
                1. enclosure:hw:disk, node:os:disk_space, node:interface:nw:cable etc
                    and the hierarchy may increase in future.
                2. enclosure, iem
                Hence splitting the above by colon(:) and assingning the last element from the split
                to module_type
                """
                module_type = res_split[len(res_split) - 1]
                """ Convert  the SSPL Schema to CSM Schema. """
                input_alert_payload = Payload(JsonMessage(message))
                csm_alert_payload = Payload(Dict(dict()))
                input_alert_payload.convert(self.mapping_dict.get\
                        (const.COMMON), csm_alert_payload)
                resource_mapping = self.mapping_dict.get(resource_type, "")
                if resource_mapping:
                    input_alert_payload.convert(resource_mapping, csm_alert_payload)
                csm_alert_payload.dump()
                csm_schema = csm_alert_payload.load()
                obj_extended_info = JsonMessage(csm_schema[const.ALERT_EXTENDED_INFO])
                """
                Fetching the health information from the alert.
                Currently we require 3 values 1. health, 2. health_reason and
                3. health_description. All these values are fetched from
                specific_info but due to specific_info can be a dict and a list
                for some alerts so we cannnot include it in mapping file.
                """
                specific_info = csm_schema.get(const.ALERT_EXTENDED_INFO)\
                    .get(const.SPECIFIC_INFO)
                if module_type != const.IEM:
                    self._set_health_info(csm_schema, specific_info)
                # TODO
                """
                1. Currently we are not consuming alert_type so keeping the 
                placeholder for now.
                2. alert_type should be derived from SSPL message's
                info.resource_type field
                3. Once a requirement comes for consuming alert_type, we should
                make use of info.resource_type and derive the alert type. 
                csm_schema[const.ALERT_TYPE] = const.HW 
                """

                """
                Below mentioned fields are managed by CSM so they are not the part
                of mapping table
                """
                csm_schema[const.ALERT_NODE_ID] = csm_schema.get\
                    (const.ALERT_EXTENDED_INFO).get(const.ALERT_INFO)\
                    .get(const.ALERT_NODE_ID)
                csm_schema[const.ALERT_RESOURCE_ID] = csm_schema.get\
                    (const.ALERT_EXTENDED_INFO).get(const.ALERT_INFO)\
                    .get(const.ALERT_RESOURCE_ID)
                csm_schema[const.ALERT_MODULE_TYPE] = f'{module_type}'
                csm_schema[const.ALERT_MODULE_NAME] = resource_type
                csm_schema[const.ALERT_CREATED_TIME] = \
                    int(csm_schema[const.ALERT_CREATED_TIME])
                csm_schema[const.ALERT_UPDATED_TIME] = int(time.time())
                csm_schema[const.ALERT_RESOLVED] = False
                csm_schema[const.ALERT_ACKNOWLEDGED] = False
                csm_schema[const.ALERT_COMMENT] = ""
                csm_schema[const.SUPPORT_MESSAGE] = ""
                """
                1. Event Details field is of type List and will conatin array of
                specific info dictionary. 
                2. Not all the fields from SSPL's specific info is consumed.
                3. Only those values are consumed which we need to display on the
                new Alert details UI page.
                4. Sensor Info is of type string and contains the concatinated
                values of site_id, node_id, rack_id, cluster_id and resource_id
                from SSPL's info section of the alert message.
                5. This string uniquely identifies the resource for which an
                alert has come.
                """
                csm_schema[const.ALERT_SENSOR_INFO] = \
                    '_'.join(str(x) for x in csm_schema[const.ALERT_SENSOR_INFO].values())
                csm_schema[const.ALERT_SENSOR_INFO] = \
                    csm_schema[const.ALERT_SENSOR_INFO].replace(" ", "_")
                if const.ALERT_EVENTS in csm_schema and \
                        csm_schema[const.ALERT_EVENTS] is not None:
                    csm_schema[const.ALERT_EVENT_DETAILS] = []
                    obj_event_details = JsonMessage(csm_schema[const.ALERT_EVENT_DETAILS])
                    self._prepare_specific_info(csm_schema, specific_info)
                    csm_schema.pop(const.ALERT_EVENTS)
                    csm_schema[const.ALERT_EVENT_DETAILS]= \
                        obj_event_details.dump(csm_schema[const.ALERT_EVENT_DETAILS])
                csm_schema[const.ALERT_EXTENDED_INFO] = \
                    obj_extended_info.dump(csm_schema[const.ALERT_EXTENDED_INFO])
        except Exception as e:
            Log.error(f"Error occured in coverting alert to csm schema. {e}")
        Log.debug(f"Converted schema:{csm_schema}")
        return csm_schema

    def _prepare_specific_info(self, csm_schema, specific_info):
        """
        This method prepares event_details for all the alerts. event_details
        comprises of some specific fields for each resource type like
        health-reason, health-recommendation and other specific fields.
        :param csm_schema : Dict containing csm alert message format
        :return : None
        """
        if csm_schema[const.ALERT_MODULE_TYPE] in (const.ALERT_LOGICAL_VOLUME,
                                                   const.ALERT_VOLUME,
                                                   const.ALERT_SIDEPLANE,
                                                   const.ALERT_FAN):
            for items in csm_schema[const.ALERT_EVENTS]:
                description_dict = {}
                """
                1. For logical_volume, volume, sideplane and fan we get a list of
                dictionaries conayining name, health-reason and
                health-recommendaion.
                2. For Sideplane expander we do not get name as a key instead we
                get component-id.
                """
                if const.ALERT_NAME in items:
                    description_dict[const.ALERT_NAME] = items[const.ALERT_NAME]
                elif const.ALERT_COMPONENT_ID in items:
                    description_dict[const.ALERT_NAME] = \
                        items[const.ALERT_COMPONENT_ID]
                description_dict[const.ALERT_EVENT_REASON] = \
                    items[const.ALERT_HEALTH_REASON]
                description_dict[const.ALERT_EVENT_RECOMMENDATION] = \
                    items[const.ALERT_HEALTH_RECOMMENDATION]
                csm_schema[const.ALERT_EVENT_DETAILS].append(description_dict)

    def _set_health_info(self, csm_schema, specific_info):
        try:
            if not isinstance(specific_info, list):
                csm_schema[const.ALERT_HEALTH] = \
                    specific_info.get(const.ALERT_HEALTH, "")
                csm_schema[const.ALERT_HEALTH_RECOMMENDATION] = \
                    specific_info.get(const.ALERT_HEALTH_RECOMMENDATION, "")
        except Exception as e:
            Log.warn(f"Unable to fetch health fields from alert. {e}")

class DecisionMakerService(Service):
    def __init__(self):
        super().__init__()
        self._decision_maker = None
        if DecisionMaker:
            self._decision_maker = DecisionMaker()

    def decision_maker_callback(self, alert_data):
        self._transmit_alerts_info(alert_data)

    def _transmit_alerts_info(self, alert_data):
        """
        This Method will send the alert to HA system for System check.
        :param alert_data: alert data received from SSPL :type:Dict
        :return: None
        """
        error = ""
        if self._decision_maker:
            for count in range(0, const.ALERT_RETRY_COUNT):
                try:
                    Log.debug(f"Sending Alert to Decision Maker for data {alert_data}")
                    self._run_coroutine(self._decision_maker.handle_alert(alert_data))
                except Exception as e:
                    Log.debug(f"retrying decision_maker {count} : {e}")
                    error = f"{e}"
                    time.sleep(2**count)
                    continue
                break
            else:
                Log.error(f"Decision Maker Failed {error} for data {alert_data}")
