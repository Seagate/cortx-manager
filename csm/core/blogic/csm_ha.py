#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          csm_resource_agent.py
 Description:       Manage CSM Resources

 Creation Date:     03/08/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.common.payload import *
from csm.common.conf import Conf
from csm.common import const
from csm.common.cluster import Cluster
from csm.common.ha_framework import *

class CsmHA:
    def __init__(self, args):
        self._resources = Conf.get(const.CSM_GLOBAL_INDEX, 'HA.resources')
        self._cluster = Cluster(const.INVENTORY_FILE)
        self._csm_resource_agents = {
            "csm_resource_agent": CsmResourceAgent(self._resources)
        }
        self._ha = HAFramework(self._csm_resource_agents)

    def init(self):
        results =  self._cluster.init(self._ha)
        for result in results:
            if not result:
                return "HA not initalized"
        return "HA initalized Successfully"

class CsmResourceAgent(ResourceAgent):

    def __init__(self, resources):
        pass

    def init(self):
        ''' Perform initalization for CSM resources '''
        #TODO- Add HA Configuration
        return True

    def failover(self):
        #TODO
        pass
