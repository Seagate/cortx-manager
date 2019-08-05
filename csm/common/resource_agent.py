#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          resource_agent.py
 Description:       Manage resources

 Creation Date:     29/07/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os, sys
import subprocess
from abc import ABC, abstractmethod

from csm.common.log import Log
from csm.common import const
from csm.common.conf import Conf
from csm.common.payload import *
from csm.common.errors import CsmError

class ResourceAgent(ABC):
    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def get_state(self):
        pass

    @abstractmethod
    def failover(self):
        pass

    @abstractmethod
    def is_available(self):
        pass

class PCSResourceAgent(ResourceAgent):
    '''
    It will use Haframework for managing resource. ResourceAgent
    can manage and monitor single or list of resources.
    '''
    def __init__(self, resources):
        self._resources = resources

    def init(self):
        pass

    def failover(self):
        pass

    def start(self):
        pass

    def stop(self):
        ''' Disable resource '''
        pass

    def is_available(self):
        pass

    def get_state(self):
        '''
        Return code:
            Primary      : 1    primary-node if resource started on primary node
            Seconday     : 2    secondary-node if resource started on swcondary node
            Stopped      : 3    Stopped if resource is Stopped
            Failed       : 4    Failed if resource is in fail or unknown state
        '''
        pass
