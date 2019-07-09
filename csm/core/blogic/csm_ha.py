#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          csm_ha.py
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

import os
import subprocess

from csm.common.log import Log
from csm.common.payload import *
from csm.common.conf import Conf
from csm.common.errors import CsmError
from csm.core.blogic import const
from csm.common.ha_framework import PcsHAFramework, PcsResourceAgent

class CsmResourceAgent(PcsResourceAgent):
    ''' Provide initalization on csm resources '''

    def __init__(self, resources):
        super(CsmResourceAgent, self).__init__(resources)
        self._resources = resources
        self._csm_index = const.CSM_GLOBAL_INDEX
        self._primary = Conf.get(const.CSM_GLOBAL_INDEX, "HA.primary")
        self._secondary = Conf.get(const.CSM_GLOBAL_INDEX, "HA.secondary")

    def init(self, force_flag):
        ''' Perform initalization for CSM resources '''
        try:
            Log.info("Starting configuring HA for CSM..")

            if force_flag:
                if self.is_available():
                    self._delete_resource()
                if os.path.exists(const.HA_INIT):
                    os.remove(const.HA_INIT)

            # Check if resource already configured
            if os.path.exists(const.HA_INIT):
                Log.info("Csm resources are already configured...")
                return True

            self._ra_init()

            for resource in self._resources:
                service = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES." + resource + ".service")
                provider = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES." + resource + ".provider")
                interval = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES." + resource + ".interval")
                timeout = Conf.get(const.CSM_GLOBAL_INDEX, "RESOURCES." + resource + ".timeout")
                self._init_resource(resource, service, provider, interval, timeout)

            # TODO- check score for failback
            self._init_constraint("INFINITY")
            self._execute_config()
            open(const.HA_INIT, 'a').close()
            Log.info("Successed: Configuring HA for CSM..")
            return True
        except CsmError as err:
            Log.exception("%s" %err)
            raise CsmError(-1, "Error: Unable to configure csm resources...")

    def failover(self):
        #TODO
        pass
