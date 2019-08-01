#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          ha_framework.py
 Description:       HAFramework manages resources.

 Creation Date:     02/08/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os

class HAFramework:
    def __init__(self, resource_agents):
        self._resource_agents = resource_agents

    def init(self):
        _results = []
        for ra_index in self._resource_agents.keys():
            _results.append(self._resource_agents[ra_index].init())
        return _results

    def failover(self):
        pass

    def is_available(self):
        pass

class ResourceAgent:
    def __init__(self):
        self._resources = resources

    def init(self, resources):
        pass

    def get_state(self):
        pass

    def failover(self):
        pass

    def is_available(self):
        pass
