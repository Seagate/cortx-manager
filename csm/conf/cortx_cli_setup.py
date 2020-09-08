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

import os
import sys
import crypt
import pwd
import grp
import shlex
import json
from eos.utils.log import Log
from csm.common.conf import Conf
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from csm.common.errors import CsmSetupError, InvalidRequest
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.common.ha_framework import PcsHAFramework
from csm.common.cluster import Cluster
from csm.core.agent.api import CsmApi
import re
import time
import traceback
import asyncio
from csm.core.blogic.models.alerts import AlertModel
from csm.core.services.alerts import AlertRepository
from eos.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.conf.setup import Setup
import ipaddress;

# try:
#     from salt import client
# except ModuleNotFoundError:
client = None

class InvalidPillarDataError(InvalidRequest):
    pass
class PillarDataFetchError(InvalidRequest):
    pass

class ProvisionerCliError(InvalidRequest):
    pass


# TODO: Devide changes in backend and frontend
# TODO: Optimise use of args for like product, force, component
class CortxCliSetup(Setup):
    def __init__(self):
        super(CortxCliSetup, self).__init__()
        self._replacement_node_flag = os.environ.get("REPLACEMENT_NODE") == "true"
        if self._replacement_node_flag:
            Log.info("REPLACEMENT_NODE flag is set")

    def _verify_args(self, args):
        """
        Verify args for actions
        """
        if "Product" in args.keys() and args["Product"] != "cortx":
            raise Exception("Not implemented for Product %s" %args["Product"])
        if "Component" in args.keys() and args["Component"] != "all":
            raise Exception("Not implemented for Component %s" %args["Component"])
        if const.ADDRESS_PARAM in args.keys():
            try:
                ipaddress.ip_address(args[const.ADDRESS_PARAM])
            except ValueError:
                raise Exception("Incorrect ip address %s" %args[const.ADDRESS_PARAM])

    def config(self, args):
        """
        Perform configuration for csm
            : Move conf file to etc
        Config is used to move update conf files one time configuration
        """
        try:
            self._verify_args(args)
            self.Config.cli_create(args)
        except Exception as e:
            raise CsmSetupError(f"cortxcli_setup config failed. Error: {e} - {str(traceback.print_exc())}")

    def refresh_config(self, args):
        """
        Refresh context for CSM
        """
        try:
            node_id = self._get_faulty_node_uuid()
            self._resolve_faulty_node_alerts(node_id)
            Log.logger.info(f"Resolved and acknowledged all the faulty node : {node_id} alerts")
        except Exception as e:
            raise CsmSetupError("cortxcli_setup refresh_config failed. Error: %s" %e)
