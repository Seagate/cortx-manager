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
from cortx.utils.service.service_handler import Service
from csm.common.payload import Text
from cortx.utils.log import Log
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_pkg import PkgV
from csm.conf.setup import Setup
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL, CsmSetupError


class PostInstall(Setup):
    """
    Post-install CORTX CLI

    Post install is used after just all rpms are install but
    no service are started
    """

    def __init__(self):
        super(PostInstall, self).__init__()

    async def execute(self, command):
        """
        Execute CORTX CLI setup Post-install Command

        :param command: Command Object For CLI. :type: Command
        :return: 0 on success, RC != 0 otherwise.
        """

        Log.info("Executing Post-install for CORTX CLI")
        self.validate_3rd_party_pkgs()
        self._configure_rsyslog()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def validate_3rd_party_pkgs(self):
        try:
            Log.info("Valdating  3rd party Python Packages")
            PkgV().validate("pip3s", self.fetch_python_pkgs())
        except VError as ve:
            Log.error(f"Failed at package Validation: {ve}")
            raise CsmSetupError(f"Failed at package Validation: {ve}")

    def fetch_python_pkgs(self):
        try:
            pkgs_data = Text(const.python_pkgs_req_path).load()
            return {ele.split("==")[0]:ele.split("==")[1] for ele in pkgs_data.splitlines()}
        except Exception as e:
            Log.error(f"Failed to fetch python packages: {e}")
            raise CsmSetupError("Failed to fetch python packages")

    def _configure_rsyslog(self):
        """
        Configure rsyslog
        """
        Log.info("Configuring rsyslog")
        os.makedirs(const.RSYSLOG_DIR, exist_ok=True)
        if os.path.exists(const.RSYSLOG_DIR):
            Setup._run_cmd(f"cp -f {const.CLI_SOURCE_SUPPORT_BUNDLE_CONF} {const.RSYSLOG_DIR}")
            Setup._run_cmd(f"cp -f {const.CLI_SOURCE_RSYSLOG_PATH} {const.RSYSLOG_DIR}")
            Log.info("Restarting rsyslog service")
            service_obj = Service('rsyslog.service')
            service_obj.restart()
        else:
            msg = f"rsyslog failed. {const.RSYSLOG_DIR} directory missing."
            Log.error(msg)
            raise CsmSetupError(msg)
