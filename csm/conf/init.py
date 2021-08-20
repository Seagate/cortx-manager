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
from cortx.utils.kv_store.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.validator.error import VError

class Init(Setup):
    """

    """
    def __init__(self):
        """
        Perform init operation for csm_setup
        """
        super(Init, self).__init__()

    async def execute(self, command):
        """

        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
        self._prepare_and_validate_confstore_keys()
        self._config_user_permission()
        #TODO: conf key check for systemd
        if Conf.get(const.CONSUMER_INDEX, f"{const.SYSTEMD}>{const.SYSTEMD_ENABLE}"):
            self.ConfigServer.reload()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}"
        })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def _config_user_permission(self, reset=False):
        """
        Allow permission for csm resources
        """
        Log.info("Allow permission for csm resources")
        crt = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS>certificate_path")
        key = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS>private_key_path")
        self._config_user_permission_set(crt, key)

    def _config_user_permission_set(self, crt, key):
        """
        Set User Permission
        """
        self._set_service_user()
        Log.info("Set User Permission")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        os.makedirs(const.CSM_PIDFILE_PATH, exist_ok=True)
        os.makedirs(log_path, exist_ok=True)
        os.makedirs(const.PROVISIONER_LOG_FILE_PATH, exist_ok=True)
        os.makedirs(const.CSM_TMP_FILE_CACHE_DIR, exist_ok=True)
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.CSM_PATH}")
        Setup._run_cmd((f"setfacl -R -m u:{self._user}:rwx "
                        f"{const.CSM_TMP_FILE_CACHE_DIR}"))
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {log_path}")
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.CSM_CONF_PATH}")
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.CSM_PIDFILE_PATH}")
        Setup._run_cmd(f"setfacl -R -m u:{self._user}:rwx {const.PROVISIONER_LOG_FILE_PATH}")
        # Setup._run_cmd(f"setfacl -R -b {const.CSM_USER_HOME}")
        if os.path.exists(crt):
            Setup._run_cmd(f"setfacl -m u:{self._user}:rwx {crt}")
        if os.path.exists(key):
            Setup._run_cmd(f"setfacl -m u:{self._user}:rwx {key}")
        Setup._run_cmd("chmod +x /opt/seagate/cortx/csm/scripts/cortxha_shutdown_cron.sh")
