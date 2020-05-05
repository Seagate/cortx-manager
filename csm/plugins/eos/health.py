#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          health.py
 Description:       Contains functionality for health plugin.

 Creation Date:     14/03/2020
 Author:            Pawan Kumar Srivastava

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import os
import time
from csm.common.comm import AmqpActuatorComm
from csm.common.errors import CsmError
from eos.utils.log import Log
from csm.common.payload import Payload, Json, JsonMessage, Dict
from csm.common.plugin import CsmPlugin
from csm.core.blogic import const
from marshmallow import Schema, fields, ValidationError
import ast
from datetime import datetime
import uuid
from csm.common.conf import Conf

class HealthPlugin(CsmPlugin):
    """
    Health Plugin is responsible for listening and sending on the comm channel.
    It has a callback which is called to send the received response to health
    service.. 
    Note, Health Plugin needs to be called in thread context as it blocks while
    listening for the response.
    """

    def __init__(self):
        super().__init__()
        try:
            self.comm_client = AmqpActuatorComm()
            self.health_callback = None
            self._health_mapping_dict = Json(const.HEALTH_MAPPING_TABLE).load()
            storage_request_path = Conf.get(const.CSM_GLOBAL_INDEX, \
                    'HEALTH.storage_actuator_request')
            node_request_path = Conf.get(const.CSM_GLOBAL_INDEX, \
                    'HEALTH.node_actuator_request')
            self._storage_request_dict = Json(storage_request_path).load()
            self._node_request_dict = Json(node_request_path).load()
            self._no_of_request = 0
            self._no_of_responses = 0
        except Exception as e:
            Log.exception(e)

    def _send_actuator_request_payload(self):
        today = datetime.now()
        try:
            if self._health_mapping_dict:
                for key in self._health_mapping_dict:
                    if key.split(':')[0] == const.ENCLOSURE:
                        self._send_encl_request(key, today)
                    elif key.split(':')[0] == const.NODE:
                        self._send_node_request(key, today)
        except Exception as ex:
            Log.warn(f"Sending actuator request failed. Reason : {ex}")

    def _send_encl_request(self, key, today):
        try:
            self._storage_request_dict[const.TIME] = str(today)
            self._storage_request_dict[const.ALERT_MESSAGE][const.HEADER]\
                    [const.UUID] = str(uuid.uuid1())
            self._storage_request_dict[const.ALERT_MESSAGE][const.ACT_REQ_TYPE]\
                    [const.STORAGE_ENCL][const.ENCL_REQ] = const.ENCL + str(key)
            self.comm_client.send(self._storage_request_dict, \
                    is_storage_request = True)
            self._no_of_request+=1
            Log.debug(f"Sent storage enclosure request for : {key}")
        except Exception as ex:
            Log.warn(f"Sending enclosure request failed. Reason : {ex}")

    def _send_node_request(self, key, today):
        try:
            self._node_request_dict[const.TIME] = str(today)
            self._node_request_dict[const.ALERT_MESSAGE][const.HEADER]\
                    [const.UUID] = str(uuid.uuid1())
            self._node_request_dict[const.ALERT_MESSAGE][const.ACT_REQ_TYPE]\
                    [const.NODE_CONTROLLER][const.NODE_REQ] = const.NODE_HW + \
                    str(key)
            self.comm_client.send(self._node_request_dict, \
                    is_storage_request = False)
            """
            Incrementing number of request with 2 as we will be sending
            requests for both node1 and node2.
            """
            self._no_of_request+=2
            Log.debug(f"Sent node request for : {key}")
        except Exception as ex:
            Log.warn(f"Sending node request failed. Reason : {ex}")

    def init(self, callback_fn, db_update_callback_fn):
        """
        Establish connection with the RMQ Server.
        Parameters -
        1. callback_fn :- This parameter specifies the name of HealthMonitor 
           class function to which plugin will send the response as JSON string.
        2. db_update_callback_fn :- This parameter specifies the name of
           HealthMonitor class function to update health map using db.
        """
        self.health_callback = callback_fn
        self.db_update_callback = db_update_callback_fn
        self.comm_client.init()

    def process_request(self, **kwargs):
        for key, value in kwargs.items():
            if key == const.CSM_ALERT_CMD and value.strip() == 'send':
                self._send()

    def health_plugin_callback(self, message):
        """
        1. This is the callback method on which we will receive the 
           response from Comm class.
        Parameters -
        1. message - Actual actuator response as  JSON string
        """
        status = False
        if self.health_callback:
            try:
                self._no_of_responses+=1
                msg_body = self._parse_response(message)
                status = self.health_callback(msg_body)
                if self._no_of_request == self._no_of_responses:
                    self.db_update_callback()
            except Exception as e:
                Log.warn(f"SOme issue occured in parsing and updating health: {e}")
        return status

    def update_health_map_with_alert(self, alert):
        health_schema = {}
        try:
            health_schema = self._parse_alert(alert)
            status = self.health_callback(health_schema)
            if status:
                Log.debug(f"Updation of health map by alert successfull. status: {status}")
        except Exception as ex:
            Log.warn(f"Updation of health map by alert failed. {ex}")

    def _parse_alert(self, message):
        resource_schema = {}
        try:
            Log.debug(f"Converting alert to health schema : {message}")
            resource_schema[const.RESOURCE_LIST] = []
            resources = {}
            extended_info = ast.literal_eval(message.get(const.ALERT_EXTENDED_INFO))
            info = extended_info.get(const.ALERT_INFO)
            resource_type = info.get(const.ALERT_RESOURCE_TYPE, "")
            mapping_dict = self._health_mapping_dict.get(resource_type, "")
            mapping_key = mapping_dict.get(const.KEY, "")
            resource_schema[const.ALERT_NODE_ID] = message.get(const.HOST_ID, "")
            resource_schema[const.ALERT_SITE_ID] = info.get(const.ALERT_SITE_ID, "")
            resource_schema[const.ALERT_RACK_ID] = info.get(const.ALERT_RACK_ID, "")
            resource_schema[const.ALERT_RESOURCE_TYPE] = resource_type
            resource_schema[const.FETCH_TIME] = message.get(const.CREATED_TIME, "")
            resource_schema[const.HEALTH_ALERT_TYPE] = \
                    message.get(const.ALERT_STATE, "")
            resource_schema[const.ALERT_SEVERITY] = \
                    message.get(const.ALERT_SEVERITY, "")
            resource_schema[const.ALERT_UUID] = message.get(const.ALERT_UUID, "")
            resource_schema[const.MAPPING_KEY] = mapping_key
            if "node" in resource_type.lower():
                resource_schema[const.NODE_RESPONSE] = True
            else:
                resource_schema[const.NODE_RESPONSE] = False
            resource_schema[const.RESOURCE_KEY] = \
                    self._prepare_resource_key(resource_schema)
            resources[const.DURABLE_ID] = extended_info.get(const.DURABLE_ID, "")
            resources[const.KEY] = resource_type + "-" + \
                    info.get(const.ALERT_RESOURCE_ID, "")
            resources[const.ALERT_HEALTH] = self._derive_health(message, \
                resource_schema[const.HEALTH_ALERT_TYPE])
            resource_schema[const.RESOURCE_LIST].append(resources)
        except Exception as ex:
            Log.warn(f"Parsing of health map by alert failed. {ex}")
        return resource_schema

    def _derive_health(self, message, alert_type):
        """
        Since SSPl is not sending health for some resources so we will have
        to derive the health based on the alert_type.
        If we are receiving a non-empty health key we will use that health value
        """
        health = ""
        if const.ALERT_HEALTH in message:
            health = message.get(const.ALERT_HEALTH)
        """
        There can be two cases -
        1. We have the health key but it has no valur. i.e 'health': ''
        2. The health key itself is missing from the paylod.
        In both the cases we need to derive the health based on alert_type.
        """
        if not health:
            if alert_type in const.BAD_ALERT:
                health = const.FAULT_HEALTH
            else:
                health = const.OK_HEALTH
        return health

    def _parse_response(self, message):
        health_schema = {}
        mapping_dict = {}
        try:
            json_msg_obj = JsonMessage(message)
            msg_body = json_msg_obj.load()
            Log.debug(f"Converting to health schema : {msg_body}")
            actuator_response =  msg_body.get(const.ALERT_MESSAGE, {}).get( \
                    "actuator_response_type", {})
            if actuator_response:
                info = actuator_response.get(const.ALERT_INFO, {})
                resource_type = info.get(const.ALERT_RESOURCE_TYPE, "")
                if resource_type:
                    actuator_payload = Payload(JsonMessage(message))
                    health_payload = Payload(Dict(dict()))
                    mapping_dict = self._health_mapping_dict.get(resource_type, "")
                    mapping_key = mapping_dict.get(const.KEY, "")
                    health_field = mapping_dict.get(const.HEALTH_FIELD, "")
                    res_id_field = mapping_dict.get(const.RES_ID_FIELD, "")
                    actuator_payload.convert(mapping_dict, health_payload)
                    health_payload.dump()
                    health_schema = health_payload.load()
                    health_schema[const.MAPPING_KEY] = mapping_key
                    health_schema[const.RESOURCE_KEY] = \
                            self._prepare_resource_key(health_schema)
                    if "node" in resource_type.lower():
                        health_schema[const.NODE_RESPONSE] = True
                    else:
                        health_schema[const.NODE_RESPONSE] = False
                    self._parse_specific_info(health_schema, health_field, res_id_field)
                    health_schema.pop(const.SPECIFIC_INFO, None)
        except Exception as ex:
            Log.warn(f"Schema conversion failed:{ex}")
        return health_schema

    def _parse_specific_info(self, health_schema, health_field, res_id_field):
        health_schema[const.RESOURCE_LIST] = []
        for items in health_schema.get(const.SPECIFIC_INFO, []):
            resources = {}
            resources[const.DURABLE_ID] = items.get(const.ALERT_DURABLE_ID, "")
            """
            Where 'health' key is missing we will replace the value with 'NA'
            """
            resources[const.ALERT_HEALTH] = items.get(health_field, const.NA_HEALTH)
            """
            There might be a situation where we have 'health' as the key but
            its value is empty, i.e 'health': ''.
            In that scenario we will replace it with 'NA'
            """
            if not resources[const.ALERT_HEALTH]:
                resources[const.ALERT_HEALTH] = const.NA_HEALTH
            resources[const.KEY] = health_schema.get\
                    (const.ALERT_RESOURCE_TYPE, "") + '-' + items.get(res_id_field, "")
            health_schema[const.RESOURCE_LIST].append(resources)

    def _prepare_resource_key(self, health_schema):
        """
        Gets the health schema key
        :param health:
        :param extended_info:
        :param resource_key:
        :return:
        """
        mapping_key = health_schema.get(const.MAPPING_KEY, "")
        try:
            resource_key = mapping_key\
            .replace(const.ALERT_SITE_ID, str(health_schema.get(const.ALERT_SITE_ID, "")))\
            .replace(const.ALERT_RACK_ID, str(health_schema.get(const.ALERT_RACK_ID, "")))\
            .replace(const.ALERT_NODE_ID, health_schema.get(const.ALERT_NODE_ID, ""))
        except Exception as ex:
            Log.warn(f"Preaparation of resource key failed : {ex}")    
        return resource_key

    def _send(self):
        """
        This is thread function.
        This method sends the actuator request to RMQ for receiving health of
        resources.
        """
        try:
            """
            Create and send actuator request.
            """
            self._send_actuator_request_payload()
        except Exception as e:
            Log.warn(e)

    def stop(self):
        """
        This method will call comm's stop to stop consuming from the queue.
        """
        self.comm_client.stop()
