#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          health.py
 Description:       Services for system health

 Creation Date:     02/20/2020
 Author:            Soniya Moholkar
                    Pawan Kumar Srivastava

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from csm.core.blogic import const
from csm.common.services import Service, ApplicationService
from csm.common.payload import Payload, Json
from csm.core.blogic.models.alerts import AlertModel
from csm.common.conf import Conf
from csm.common.log import Log
from csm.common.observer import Observable
from threading import Event, Thread
from csm.core.services.alerts import AlertRepository
import asyncio

class HealthRepository:
    def __init__(self):        
        self._health_schema = None     

    @property
    def health_schema(self):
        """
        returns health schema
        :param None
        :returns: health_schema
        """
        return self._health_schema

    @health_schema.setter
    def health_schema(self, health_schema):
        """
        sets health schema
        :param health_schema
        :returns: None
        """
        self._health_schema = health_schema    

class HealthAppService(ApplicationService):
    """
        Provides operations on in memory health schema
    """

    def __init__(self, repo: HealthRepository):
        self.repo = repo
        self._init_health_schema()

    def _init_health_schema(self):
        health_schema_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                      'HEALTH.health_schema')
        self._health_schema = Payload(Json(health_schema_path))
        self.repo.health_schema = self._health_schema
        self.repo.health_schema.dump()

    async def fetch_health_summary(self):
        """
        Fetch health summary from in-memory health schema
        1.) Gets the health schema from repo
        2.) Counts the resources as per their health
        :param None
        :returns: Health Summary Json
        """
        health_schema = self.repo.health_schema._data
        health_count_map = {}
        leaf_nodes = []
        self._get_leaf_node_health(health_schema, health_count_map, leaf_nodes)
        bad_health_count = 0
        total_leaf_nodes = len(leaf_nodes)
        health_summary={}
        health_summary[const.TOTAL] = total_leaf_nodes
        for x in health_count_map:
            if(x != const.OK_HEALTH):
                health_summary[x] = health_count_map[x]
                bad_health_count += health_count_map[x]
        good_health_count = total_leaf_nodes - bad_health_count
        health_summary[const.GOOD_HEALTH] = good_health_count
        return {const.HEALTH_SUMMARY: {x: health_summary[x] for x in health_summary}}
        
    def _get_leaf_node_health(self, health_schema, health_count_map, leaf_nodes):
        """
        Identify non-empty leaf nodes of in-memory health schema
        and get health summary.
        1.) Checks if the schema has child
        2.) checks if the child is dict
        3.) check if the dict is non-empty
        4.) leaf node is identified based on
            i.) it doesn't have child dict
            ii.) it is not empty
        5.) as leaf node is identified the total count of leaf nodes
            is increased by 1
        :param health schema, health_count_map, leaf_nodes
        :returns: Health Summary Json
        """
        def checkchilddict(health_schema):
            for k, v in health_schema.items():
                if isinstance(v, dict):
                    return True

        def isempty(health_schema):
            if(health_schema.items()):
                return False
            return True

        for k, v in health_schema.items():
            if isinstance(v, dict):
                if(checkchilddict(v)):
                    self._get_leaf_node_health(v, health_count_map, leaf_nodes)
                else:
                    if(not isempty(v)):
                        leaf_nodes.append(v)
                        if (const.HEALTH in v):
                            if (v[const.HEALTH] in health_count_map):
                                health_count_map[v[const.HEALTH]] += 1
                            else:
                                health_count_map[v[const.HEALTH]] = 1

    def update_health_map(self, msg_body):
        Log.debug(f"Updating health map : {msg_body}")
        try:
            for items in msg_body.get("resource_list", []):
                resource_key = items.get("resource_key", "")
                resource_map = self.repo.health_schema.get\
                        (resource_key)
                key = items.get("key", "")
                resource_schema_dict = self._get_health_schema_by_key\
                        (resource_map, key)
                if resource_schema_dict:
                    resource_schema_dict[const.HEALTH_ALERT_TYPE] \
                        = msg_body.get(const.HEALTH_ALERT_TYPE, "")
                    resource_schema_dict[const.ALERT_SEVERITY] \
                        = msg_body.get(const.ALERT_SEVERITY, "")
                    resource_schema_dict[const.ALERT_UUID] \
                        = msg_body.get(const.ALERT_UUID, "")
                    resource_schema_dict["fetch_time"] \
                        = msg_body.get("fetch_time", "")
                    resource_schema_dict[const.ALERT_HEALTH] \
                        = items.get(const.ALERT_HEALTH, "")
                    resource_schema_dict["durable_id"] \
                        = items.get("durable_id", "")
                    self._set_health_schema_by_key\
                            (resource_map, items.get("key", ""), resource_schema_dict)
                    Log.debug(f"Health map updated for: {key}")
                else:
                    Log.warn(f"Resource not found in health map. Key :{key}")
        except Exception as ex:
            Log.warn(f"Health Map Updation failed :{msg_body}")

       
    def _checkchilddict(self, obj):
        """
        Check if the obj has child dicts
        :param obj:
        :return:
        """
        for k, v in obj.items():
            if isinstance(v, dict):
                return True

    def _get_health_schema_by_key(self, obj, key):
        """
        Get the schema for the provided key
        :param obj:
        :param node_key:
        :return:
        """
        def getvalue(obj):
            try:
                for k, v in obj.items():
                    if (key == k):
                        return v

                    if isinstance(v, dict):
                        if (self._checkchilddict(v)):
                            kk = getvalue(v)
                            if kk:
                                return kk
            except Exception as ex:
                Log.warn(f"Getting health schema by key failed:{ex}")
        return getvalue(obj)

    def _set_health_schema_by_key(self, obj, key, value):
        """
        Get the schema for the provided key
        :param obj:
        :param node_key:
        :return:
        """
        def setValue(obj):
            try:
                for k, v in obj.items():
                    if (key == k):
                        obj[k] = value    

                    if isinstance(v, dict):
                        if (self._checkchilddict(v)):
                            setValue(v)
            except Exception as ex:
                Log.warn(f"Setting health schema by key failed:{ex}")

class HealthMonitorService(Service, Observable):
    """
    Health Monitor works with AmqpComm to monitor and send actuatore requests. 
    """

    def __init__(self, plugin, health_service: HealthAppService, alerts_repo:
            AlertRepository):
        """
        Initializes the Health Plugin
        """
        self._health_plugin = plugin
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._health_service = health_service
        self._alerts_repo = alerts_repo
        super().__init__()

    @property
    def health_plugin(self):
        return self._health_plugin

    def _send(self):
        """
        This method acts as a thread function. 
        It will send the actuator request.
        """
        self._thread_running = True
        self._health_plugin.init(callback_fn=self._consume,\
               db_update_callback_fn=self._update_health_schema_with_db)
        self._health_plugin.process_request(cmd='send')

    def start(self):
        """
        This method creats and starts an health monitor thread
        """
        Log.info("Starting Health monitor thread")
        try:
            if not self._thread_running and not self._thread_started:
                self._monitor_thread = Thread(target=self._send,
                                              args=())
                self._monitor_thread.start()
                self._thread_started = True
        except Exception as e:
            Log.warn(f"Error in starting health monitor thread: {e}")

    def stop(self):
        try:
            Log.info("Stopping Health monitor thread")
            self._health_plugin.stop()
            self._monitor_thread.join()
            self._thread_started = False
            self._thread_running = False
        except Exception as e:
            Log.warn(f"Error in stoping alert monitor thread: {e}")

    def _consume(self, message):
        """
        This is a callback function which will receive
        a message from the health plugin as a dictionary.
        """
        self._health_service.update_health_map(message)
        return True

    def _update_health_schema_with_db(self):
        """
        Updates the in memory health schema after CSM init.
        1.) Fetches all the non-resolved alerts from DB
        2.) Update the initialized and loaded in-memory health schema
        :param None
        :return: None
        """
        Log.debug(f"Updating health schema_with db.")
        try:
            alerts = self._run_coroutine(self._alerts_repo.retrieve_by_range(\
                    create_time_range=None, resolved=False))
            for alert in alerts:
                self.health_plugin.update_health_map_with_alert(alert.to_primitive())        
        except Exception as e:
            Log.warn(f"Error in update_health_schema_with db: {e}")
