#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          health.py
 Description:       Services for system health

 Creation Date:     02/20/2020
 Author:            Soniya Moholkar

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
from csm.core.blogic import const
from csm.common.services import Service, ApplicationService
from csm.common.payload import Payload, Json
from csm.core.blogic.models.alerts import AlertModel

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
        self._health_schema = Payload(Json(const.HEALTH_SCHEMA))
        self.repo.health_schema = self._health_schema
    
    def update_health_schema(self, alert: AlertModel):
        """
        Updates the in memory health schema after receiving alert.
        The health schema will be updated with key generated using
        health_csm_schema_key_mapping json and getting site_id, cluster_id,
        node_id, rack_id, resource_type and resource_id from alert.
        :param AlertModel: alert
        :return: None
        """
        mapping_dict = Json(const.HEALTH_CSM_SCHEMA_KEY_MAPPING).load()
        hw_health_key = mapping_dict[alert.get(const.ALERT_MODULE_NAME)]
        extended_info = eval(alert.get(const.ALERT_EXTENDED_INFO))
        if (extended_info and extended_info.get(const.ALERT_INFO)):
            resource_id = alert.get(const.ALERT_MODULE_NAME) + '-' \
                + extended_info.get(const.ALERT_INFO).get(const.ALERT_RESOURCE_ID)
            hw_health_key = hw_health_key.replace(const.ALERT_SITE_ID, 
                str(extended_info.get(const.ALERT_INFO).get(const.ALERT_SITE_ID))).replace(const.ALERT_RACK_ID, 
                str(extended_info.get(const.ALERT_INFO).get(const.ALERT_RACK_ID))).replace(const.ALERT_NODE_ID,
                str(extended_info.get(const.ALERT_INFO).get(const.ALERT_NODE_ID))).replace(const.ALERT_CLUSTER_ID,
                str(extended_info.get(const.ALERT_INFO).get(const.ALERT_CLUSTER_ID))).replace(const.ALERT_RESOURCE_ID, 
                resource_id)
            resource_schema_dict = self.repo.health_schema.get(hw_health_key)
            if(resource_schema_dict):
                resource_schema_dict['alert_type'] = alert.state
                resource_schema_dict['severity'] = alert.severity
                resource_schema_dict['alert_uuid'] = alert.alert_uuid
                resource_schema_dict['event_time'] = alert.updated_time
                resource_schema_dict['health'] = alert.state
                self._health_schema.set(hw_health_key, resource_schema_dict)

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