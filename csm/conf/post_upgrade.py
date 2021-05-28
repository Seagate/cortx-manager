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

from cortx.utils.log import Log
from csm.conf.post_install import PostInstall
from csm.conf.prepare import Prepare
from csm.conf.configure import Configure
from csm.conf.init import Init
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.conf.setup import Setup, CsmSetupError
from cortx.utils.conf_store import Conf
from cortx.utils.kv_store.error import KvError
import time
import os


class PostUpgrade(PostInstall, Prepare, Configure, Init):
    """
    Perform post-upgrade for regenerating the coonfigurations after 
    upgrade is done.    
    """

    def __init__(self):
        """Instiatiate Post Install Class."""
        Log.info("Executing Post Upgrade for CSM.")
        super(PostUpgrade, self).__init__()

    async def execute(self, command):
        """
        :param command:
        :return:
        """
        self._backup_config_dir()
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DB_SOURCE_CONF_FILE_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")

        #Postinstall functionality
        self._set_deployment_mode()
        self.validate_3rd_party_pkgs()
        self._configure_system_auto_restart()
        self._configure_system_auto_restart()
        self._configure_service_user()
        self._configure_rsyslog()
        #Prepare functionality
        self._set_secret_string_for_decryption()
        self._set_cluster_id()
        self._set_db_host_addr()
        self._set_fqdn_for_nodeid()
        self._set_s3_ldap_credentials()
        self._set_password_to_csm_user()
        #Configure functionality
        self._validate_consul_service()
        self._validate_es_service()
        self._configure_uds_keys()
        self._logrotate()
        self._configure_cron()
        for count in range(0, 10):
            try:
                await self._set_unsupported_feature_info()
                break
            except Exception as e_:
                Log.warn(f"Unable to connect to ES. Retrying : {count+1}. {e_}")
                time.sleep(2**count)
        #Init functionality
        self._config_user_permission()

    def _backup_config_dir(self):
        if os.path.exists(const.CSM_ETC_DIR):
            Log.info("Creating backup for older csm configurations")
            Setup._run_cmd(f"cp -r {const.CSM_ETC_DIR} {const.CSM_ETC_DIR}_backup")
        else:
            os.makedirs(const.CSM_ETC_DIR, exist_ok=True)
            Setup._run_cmd(f"cp -r {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")
