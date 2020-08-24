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

from csm.core.blogic import const
from typing import Optional, Iterable, Dict
from csm.common.services import Service, ApplicationService
from csm.common.payload import Payload, Json
from csm.core.blogic.models.alerts import AlertModel
from csm.common.conf import Conf
from eos.utils.log import Log
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

    def __init__(self, repo: HealthRepository, alerts_repo, plugin):
        self._health_plugin = plugin
        self.repo = repo
        self.alerts_repo = alerts_repo
        self._is_map_updated_with_db = False
        self._health_plugin = plugin
        self._init_health_schema()

    def _init_health_schema(self):
        health_schema_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                      'HEALTH.health_schema')
        try:
            self._health_schema = Payload(Json(health_schema_path))
            self.repo.health_schema = self._health_schema
            self.repo.health_schema.dump()
        except Exception as ex:
            Log.error(f"Error occured in reading health schema. Path: {health_schema_path}, {ex}")
    
    async def fetch_health_view(self, **kwargs):
        """
        Fetches health details like health summary and alerts for the provides
        node key.
        1.) If key is specified, get the schema for the provided key.
        2.) If key is not provided, get all the data for the childern under
        'nodes'
        :param kwargs:
        :return:
        """
        node_id = kwargs.get(const.ALERT_NODE_ID, "")
        node_health_details = []
        keys = []
        if node_id:
           keys.append(node_id)
        else:
            parent_health_schema = self._get_schema(const.KEY_NODES)
            keys = self._get_child_node_keys(parent_health_schema)

        for key in keys:
            node_details = await self._get_node_health_details(key)
            node_health_details.append(node_details)
        return node_health_details

    async def fetch_component_health_view(self, **kwargs):
        """
        Fetches health details like health summary and components for the provides
        node key.
        1.) If key is specified, get the schema for the provided key.
        2.) If key is not provided, get all the data for the childern under
        'nodes'
        :param kwargs:
        :return:
        """
        node_id = kwargs.get(const.ALERT_NODE_ID, "")
        node_health_details = []
        keys = []
        node_details = {}
        if node_id:
           keys.append(node_id)
        else:
            parent_health_schema = self._get_schema(const.KEY_NODES)
            keys = self._get_child_node_keys(parent_health_schema)            

        for key in keys:
            node_details = await self._get_component_details(key)
            node_health_details.append(node_details)
        return node_health_details

    async def fetch_node_health(self, **kwargs):
        """
        Fetches health details like health summary for the provided
        node key.
        1.) If key is specified, get the schema for the provided key.
        2.) If key is not provided, get all the data for the childern under
        'nodes'
        :param kwargs:
        :return:
        Health map is updated with db from health plugin after reciving all 
        the responses for actuator requests.
        There might be a situation where we did not get all the responses for
        the request we made. So, in that case the health map will not be update
        with elasticsearch db.
        So, just to make sure that the health map is updated with db we will 
        update it when we fetch health summary.
        To make sure that it gets updatesd only once either from plugin or from
        summary call, a boolean flag is maintained.
        """
        await self.update_health_schema_with_db()
        node_id = kwargs.get(const.ALERT_NODE_ID, "")
        node_health_details = []
        keys = []
        if node_id:
             keys.append(node_id)
        else:
            parent_health_schema = self._get_schema(const.KEY_NODES)
            keys = self._get_child_node_keys(parent_health_schema)

        for key in keys:
            node_details = self._get_node_health(key)
            node_health_details.append(node_details)
        return node_health_details

    async def fetch_health_summary(self , node_id: Optional[str] = None):
        """
        Fetch health summary from in-memory health schema
        1.) Gets the health schema from repo
        2.) Counts the resources as per their health
        :param None
        :returns: Health Summary Json
        Health map is updated with db from health plugin after reciving all 
        the responses for actuator requests.
        There might be a situation where we did not get all the responses for
        the request we made. So, in that case the health map will not be update
        with elasticsearch db.
        So, just to make sure that the health map is updated with db we will 
        update it when we fetch health summary.
        To make sure that it gets updatesd only once either from plugin or from
        summary call, a boolean flag is maintained.
        """
        await self.update_health_schema_with_db()
        health_schema = self._get_schema()
        health_count_map = {}
        leaf_nodes = []
        self._get_leaf_node_health(health_schema, health_count_map, leaf_nodes, {})
        return {
            const.HEALTH_SUMMARY: self._get_health_count(health_count_map, leaf_nodes)}

    async def _get_node_health_details(self, node_id):
        """
        Get health details like health summary and alerts for the provided node_id
        :param node_id:
        :return:
        """
        health_count_map = {}
        leaf_nodes = []
        alert_uuid_map = {}
        health_schema = self._get_schema(node_id)
        self._get_leaf_node_health(health_schema, health_count_map,
                                   leaf_nodes, alert_uuid_map)
        health_summary = self._get_health_count(health_count_map, leaf_nodes)
        alerts = await self._get_node_alerts(alert_uuid_map)
        node_details = {node_id: {const.HEALTH_SUMMARY: health_summary, const.ALERTS_COMMAND: alerts}}
        return node_details
    async def _get_component_details(self, node_id):
        """
        Get health details like health summary and components for the provided node_id
        :param node_id:
        :return:
        """
        health_count_map = {}
        leaf_nodes = []
        alert_uuid_map = {}
        health_schema = self._get_schema(node_id)
        self._get_leaf_node_health(health_schema, health_count_map,
                                   leaf_nodes, alert_uuid_map)
        health_summary = self._get_health_count(health_count_map, leaf_nodes)
        component_details = []

        for component in leaf_nodes:
            component_detail = {}
            component_detail["component_id"] = component.get("component_id")
            component_detail["health"] = component.get("health")
            component_detail["durable_id"] = component.get("durable_id")
            component_detail["alert_uuid"] = component.get("alert_uuid")
            component_detail["component_info"] = component
            component_details.append(component_detail)
        
        node_details = {node_id: {const.HEALTH_SUMMARY: health_summary, "components": component_details}}
        return node_details

    def _get_node_health(self, node_id):
        """
        Get health details like health summary for the provided node_id
        :param node_id:
        :return:
        """
        health_count_map = {}
        leaf_nodes = []
        alert_uuid_map = {}
        health_schema = self._get_schema(node_id)
        self._get_leaf_node_health(health_schema, health_count_map,
                                   leaf_nodes, alert_uuid_map)
        health_summary = self._get_health_count(health_count_map, leaf_nodes)
        node_details = {node_id: {const.HEALTH_SUMMARY: health_summary}}
        return node_details

    async def _get_node_alerts(self, alert_uuid_map):
        alert_ids = set()
        for x in alert_uuid_map:
            if x.lower() != const.OK_HEALTH.lower():
                alert_ids.update(alert_uuid_map.get(x, [])) 

        if alert_ids:
            alerts_list = await self.alerts_repo.retrieve_by_ids(alert_ids)
            alerts = [alert.to_primitive() for alert in alerts_list]
        return alerts

    def _get_health_count(self, health_count_map, leaf_nodes):
        """
        Get the health count based on the health status
        :param health_count_map:
        :param leaf_nodes:
        :return:
        """
        critical_health_count = 0
        warning_health_count = 0
        total_leaf_nodes = len(leaf_nodes)
        health_summary = {}
        health_summary[const.TOTAL] = total_leaf_nodes
        """
        Since we are getting health as "NA" for node sensors we will consider
        it as a good. 
        """
        for x in health_count_map:
            health = severity = x.split('-')[0]
            severity = severity = x.split('-')[1]
            if health.upper() != const.OK_HEALTH and \
                health.upper() != const.NA_HEALTH:
                if severity.upper() in [const.CRITICAL.upper(), const.ERROR.upper()]:
                    critical_health_count += health_count_map[x]
                elif severity.upper() in [const.WARNING.upper(), const.NA_HEALTH.upper(), '']:
                    warning_health_count += health_count_map[x]
        bad_health_count = critical_health_count + warning_health_count
        good_health_count = total_leaf_nodes - bad_health_count
        health_summary[const.GOOD_HEALTH] = good_health_count
        health_summary[const.CRITICAL.lower()] = critical_health_count
        health_summary[const.WARNING.lower()] = warning_health_count
        return {x: health_summary[x] for x in health_summary}

    def _get_schema(self, key: Optional[str] = None):
        """
        Get health schema based on the key provided
        :param key:
        :return:
        """
        health_schema = self.repo.health_schema.data()
        if key and not key.isspace():
            health_schema = self._get_health_schema_by_key(health_schema, key)
        return health_schema

    def _get_leaf_node_health(self, health_schema, health_count_map, leaf_nodes, alert_uuid_map):
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
        if health_schema:
            is_sas_incremented = False
            for k, v in health_schema.items():
                if isinstance(v, dict):
                    if(self._checkchilddict(v)):
                        self._get_leaf_node_health(v, health_count_map, leaf_nodes, alert_uuid_map)
                    else:
                        if v:
                            leaf_nodes.append(v)
                            v["component_id"] = k
                            health = v.get(const.ALERT_HEALTH, "").lower()
                            severity = v.get(const.ALERT_SEVERITY, "").lower()
                            health_status = f'{health}-{severity}'
                            if v.get(const.ALERT_HEALTH):
                                """
                                Here we handle the count of sas alert.
                                Since, the sas alert only comes when all the 16 
                                phy's are at fault so we need to update 16 resources
                                at a time in the health map but count should
                                increase by 1 as we receive only 1 alert.
                                """
                                if const.SAS_RESOURCE_TYPE in k:
                                    if not is_sas_incremented:
                                        if health_count_map.get(health_status):
                                            health_count_map[health_status] += 1
                                        else:
                                            health_count_map[health_status] = 1
                                        is_sas_incremented = True
                                else:
                                    if health_count_map.get(health_status):
                                        health_count_map[health_status] += 1
                                    else:
                                        health_count_map[health_status] = 1

                            if v.get(const.ALERT_UUID):
                                if alert_uuid_map.get(health_status):  
                                    alert_uuids = alert_uuid_map[health_status]
                                    if v.get(const.ALERT_UUID) not in alert_uuids:
                                        alert_uuids.append(v.get(const.ALERT_UUID))
                                else:
                                    alert_uuid_map[health_status] = [v.get(const.ALERT_UUID)]
        else:
            Log.warn(f"Empty health_schema")

    def _checkchilddict(self, obj):
        """
        Check if the obj has child dicts
        :param obj:
        :return:
        """
        for k, v in obj.items():
            if isinstance(v, dict):
                return True

    def _get_child_node_keys(self, obj):
        """
        Get the keys of the children dict for the provided obj
        :param obj:
        :return:
        """
        keys = []
        if obj: 
            for k, v in obj.items():
                if isinstance(v, dict):
                    keys.append(k)
        return keys

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

    def update_health_map(self, msg_body):
        Log.debug(f"Updating health map : {msg_body}")
        return_value = False
        try:
            resource_map = {}
            resource_node_map = {}
            update_key = None
            is_node_response = msg_body.get(const.NODE_RESPONSE, False)
            resource_key = msg_body.get(const.RESOURCE_KEY, "")
            sub_resource_map = self.repo.health_schema.get(resource_key)
            node_id = "node:" + msg_body.get(const.ALERT_NODE_ID, "")
            if is_node_response:
                resource_map = self._get_health_schema_by_key\
                        (sub_resource_map, node_id)
                update_key = node_id
            else:
                resource_map = sub_resource_map
                update_key = resource_key

            for items in msg_body.get(const.RESOURCE_LIST, []):
                key = items.get(const.KEY, "")
                resource_schema_dict = self._get_health_schema_by_key\
                        (resource_map, key)
                if resource_schema_dict:
                    resource_schema_dict[const.HEALTH_ALERT_TYPE] \
                        = msg_body.get(const.HEALTH_ALERT_TYPE, "")
                    resource_schema_dict[const.ALERT_SEVERITY] \
                        = msg_body.get(const.ALERT_SEVERITY, "")
                    resource_schema_dict[const.ALERT_UUID] \
                        = msg_body.get(const.ALERT_UUID, "")
                    resource_schema_dict[const.FETCH_TIME] \
                        = msg_body.get(const.FETCH_TIME, "")
                    resource_schema_dict[const.ALERT_HEALTH] \
                        = items.get(const.ALERT_HEALTH, "")
                    resource_schema_dict[const.ALERT_DURABLE_ID] \
                        = items.get(const.ALERT_DURABLE_ID, "")
                    self._set_health_schema_by_key\
                            (resource_map, key, resource_schema_dict)
                    Log.debug(f"Health map updated for: {key}")
                else:
                    Log.warn(f"Resource not found in health map. Key :{key}")
            """
            Updating the health map with sub-resource map
            """
            self._set_health_schema_by_key(self.repo.health_schema.data(),\
                    update_key, resource_map)
            Log.debug(f"Health map updated successfully.")
            return_value = True
        except Exception as ex:
            Log.warn(f"Health Map Updation failed :{msg_body}")
            return_value = False
        return return_value

    async def update_health_schema_with_db(self):
        """
        Updates the in memory health schema after CSM init.
        1.) Fetches all the non-resolved alerts from DB
        2.) Update the initialized and loaded in-memory health schema
        :param None
        :return: None
        """
        if not self._is_map_updated_with_db:
            Log.debug(f"Updating health schema_with db.")
            try:
                alerts = await self.alerts_repo.retrieve_by_range(create_time_range=None)
                for alert in alerts:
                    self._health_plugin.update_health_map_with_alert(alert.to_primitive())
                self._is_map_updated_with_db = True
            except Exception as e:
                Log.warn(f"Error in update_health_schema_with db: {e}")

class HealthMonitorService(Service, Observable):
    """
    Health Monitor works with AmqpComm to monitor and send actuatore requests. 
    """

    def __init__(self, plugin, health_service: HealthAppService):
        """
        Initializes the Health Plugin
        """
        self._health_plugin = plugin
        self._monitor_thread = None
        self._thread_started = False
        self._thread_running = False
        self._health_service = health_service
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
               db_update_callback_fn=self._update_map_with_db)
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
            Log.warn(f"Error in stopping health monitor thread: {e}")

    def _consume(self, message):
        """
        This is a callback function which will receive
        a message from the health plugin as a dictionary.
        """
        self._health_service.update_health_map(message)
        return True

    def _update_map_with_db(self):
        self._run_coroutine(self._health_service.update_health_schema_with_db())
