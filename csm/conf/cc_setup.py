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
        if "f" in args.keys() and args["f"] is True:
            raise Exception("Not implemented for force action")

    def post_install(self, args):
        """
        Perform post-install for csm
            : Configure csm user
            : Add Permission for csm user
            : Add cronjob for csm cleanup
        Post install is used after just all rpms are install but
        no service are started
        """
        try:
            self._verify_args(args)
            self._config_user()
            self._cleanup_job()
        except Exception as e:
            raise CsmSetupError(f"cortxcli_setup post_install failed. Error: {e} - {str(traceback.print_exc())}")

    def config(self, args):
        """
        Perform configuration for csm
            : Move conf file to etc
        Config is used to move update conf files one time configuration
        """
        try:
            self._verify_args(args)
            if not self._replacement_node_flag:
                self.Config.create(args)
        except Exception as e:
            raise CsmSetupError(f"cortxcli_setup config failed. Error: {e} - {str(traceback.print_exc())}")

    def init(self, args):
        """
        Check and move required configuration file
        Init is used after all dependency service started
        """
        try:
            self._verify_args(args)
            self.Config.load()
            self._config_user_permission()
            if not self._replacement_node_flag:
                self._set_rmq_cluster_nodes()
                #TODO: Adding this implementation in try..except block to avoid build failure
                # Its a work around and it will be fixed once EOS-10551 resolved
                try:
                    self._set_rmq_node_id()
                except Exception as e:
                    Log.error(f"Failed to fetch system node ids info from provisioner cli.- {e}")
                self._set_consul_vip()
            self.ConfigServer.reload()
            self._rsyslog()
            self._logrotate()
            self._rsyslog_common()
            ha_check = Conf.get(const.CSM_GLOBAL_INDEX, "HA.enabled")
            if ha_check:
                self._config_cluster(args)
        except Exception as e:
            raise CsmSetupError(f"cortxcli_setup init failed. Error: {e} - {str(traceback.print_exc())}")

    def reset(self, args):
        """
        Reset csm configuraion
        Soft: Soft Reset is used to restrat service with log cleanup
            - Cleanup all log
            - Reset conf
            - Restart service
        Hard: Hard reset is used to remove all configuration used by csm
            - Stop service
            - Cleanup all log
            - Delete all Dir created by csm
            - Cleanup Job
            - Disable csm service
            - Delete csm user
        """
        try:
            self._verify_args(args)
            if args["hard"]:
                self.Config.load()
                self.ConfigServer.stop()
                self._log_cleanup()
                self._config_user_permission(reset=True)
                self._cleanup_job(reset=True)
                self.Config.delete()
                self._config_user(reset=True)
            else:
                self.Config.reset()
                self.ConfigServer.restart()
        except Exception as e:
            raise CsmSetupError("cortxcli_setup reset failed. Error: %s" %e)

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
