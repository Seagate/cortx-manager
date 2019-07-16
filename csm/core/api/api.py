#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          api_client.py
 Description:       Infrastructure for invoking business logic locally or
                    remotely or various available channels like REST.

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import errno
import yaml

from csm.providers.provider_factory import ProviderFactory
from csm.common.conf import Conf
from csm.common.log import Log
from csm.common import const
from csm.common.cluster import Cluster
from csm.common.errors import CsmError

class CsmApi(object):
    """ Interface class to communicate with RAS API """
    _providers = {}
    _cluster = None
    @staticmethod
    def init():
        """ API server initialization. Validates and Loads configuration """

        Conf.init('/etc/csm.conf')
        # Validate configuration files are present
        inventory_file = Conf.get(const.INVENTORY_FILE, const.DEFAULT_INVENTORY_FILE)
        if not os.path.isfile(inventory_file):
            raise CsmError(errno.ENOENT, 'cluster config file %s does not exist' %inventory_file)


        # Read inventory data
        CsmApi._cluster = Cluster(inventory_file)

    @staticmethod
    def process_request(command_name, request, callback):
        """
        Processes requests received from client using a backend provider.
        Provider is loaded initially and instance is reused for future calls.
        """

        if CsmApi._cluster == None:
            raise CsmError(errno.ENOENT, 'CSM API not initialized')
        Log.info('command=%s action=%s args=%s' %(command_name, \
            request.action(), request.args()))
        if not command_name in CsmApi._providers.keys():
            CsmApi._providers[command_name] = \
                ProviderFactory.get_provider(command_name, CsmApi._cluster)
        provider = CsmApi._providers[command_name]
        provider.process_request(request, callback)
