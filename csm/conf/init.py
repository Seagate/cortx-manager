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
import re
import time
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kvstore.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL

class Init(Setup):
    """

    """
    def __init__(self):
        """

        """
        super(Init, self).__init__()
        self._dev_mode = False

    async def execute(self, command):
        """

        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.CORTXCLI_GLOBAL_INDEX, const.CORTXCLI_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        if Conf.get(const.CONSUMER_INDEX,
                    f"{const.CLUSTER}>{const.DEPLOYMENT}>{const.MODE}") == "DEV":
            Log.info("Setting Up CSM in Dev Mode.")
            self._dev_mode = True
        self._config_user_permission()
        self.ConfigServer.reload()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _config_user_permission(self, reset=False):
        """
        Create user and allow permission for csm resources
        """
        Log.info("Create user and allow permission for csm resources")
        bundle_path = Conf.get(const.CORTXCLI_GLOBAL_INDEX,
                               "SUPPORT_BUNDLE>bundle_path")
        crt = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS>certificate_path")
        key = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS>private_key_path")
        self._config_user_permission_set(bundle_path, crt, key)

    def _config_user_permission_set(self, bundle_path, crt, key):
        """
        Set User Permission
        """
        Log.info("Set User Permission")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
        os.makedirs(const.CSM_PIDFILE_PATH, exist_ok=True)
        os.makedirs(log_path, exist_ok=True)
        os.makedirs(bundle_path, exist_ok=True)
        os.makedirs(const.CSM_TMP_FILE_CACHE_DIR, exist_ok=True)
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.CSM_PATH}")
        Setup._run_cmd((f"setfacl -R -m u:{self._user}:rwx "
                        f"{const.CSM_TMP_FILE_CACHE_DIR}"))
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {bundle_path}")
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {log_path}")
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.CSM_CONF_PATH}")
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.CSM_PIDFILE_PATH}")
        # Setup._run_cmd(f"setfacl -R -b {const.CSM_USER_HOME}")
        if os.path.exists(crt):
            Setup._run_cmd(f"setfacl -m u:{self._user}:rwx {crt}")
        if os.path.exists(key):
            Setup._run_cmd(f"setfacl -m u:{self._user}:rwx {key}")
        Setup._run_cmd("chmod +x /opt/seagate/cortx/csm/scripts/cortxha_shutdown_cron.sh")
