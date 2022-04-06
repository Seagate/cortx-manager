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
from cortx.utils.validator.error import VError
import time
import os
from datetime import datetime
from csm.core.providers.providers import Response


class PostUpgrade(PostInstall, Prepare, Configure, Init, Setup):
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
        backup_dirname = None
        if os.path.exists(const.CSM_ETC_DIR):
            backup_dirname = PostUpgrade.__backup_config_dir()
        # TODO Multiple parents invoke this method on construction, but we need to do it again.
        self._copy_skeleton_configs()
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_CONF_URL)
            Conf.load(const.DATABASE_INDEX, const.DATABASE_CONF_URL)
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")

        self._prepare_and_validate_confstore_keys()
        #Postinstall functionality
        self.validate_3rd_party_pkgs()
        self._config_user()
        self._configure_system_auto_restart()
        self._configure_service_user()
        self._configure_rsyslog()
        #Prepare functionality
        self._set_secret_string_for_decryption()
        self._set_cluster_id()
        self._set_db_host_addr()
        self._set_fqdn_for_nodeid()
        self._set_password_to_csm_user()
        #Configure functionality
        self._configure_uds_keys()
        self._configure_csm_web_keys()
        self._logrotate()
        self._configure_cron()
        for count in range(0, 10):
            try:
                await self._set_unsupported_feature_info()
                break
            except Exception as e_:
                Log.warn(f"Unable to connect to ES. Retrying : {count+1}. {e_}")
                time.sleep(2**count)
        # Restore backup config before the init phase if it exists
        if backup_dirname is not None:
            PostUpgrade.__restore_backup_config(backup_dirname)
        #Init functionality
        self._config_user_permission()

        self.create()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SERVER_NODE_INFO:f"{const.SERVER_NODE_INFO}",
            const.KEY_SERVER_NODE_TYPE:f"{const.SERVER_NODE_INFO}>{const.TYPE}",
            const.KEY_ENCLOSURE_ID:f"{const.SERVER_NODE_INFO}>{const.STORAGE}>{const.ENCLOSURE_ID}",
            const.KEY_CSM_USER:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.USER}",
            const.KEY_DATA_NW_PRIVATE_FQDN:f"{const.SERVER_NODE_INFO}>{const.NETWORK}>{const.DATA}>{const.PRIVATE_FQDN}",
            const.KEY_HOSTNAME:f"{const.SERVER_NODE_INFO}>{const.HOSTNAME}",
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}",
            const.KEY_CSM_SECRET:f"{const.CORTX}>{const.SOFTWARE}>{const.NON_ROOT_USER}>{const.SECRET}",
            const.KEY_DATA_NW_PUBLIC_FQDN:f"{const.SERVER_NODE_INFO}>{const.NETWORK}>{const.DATA}>{const.PUBLIC_FQDN}",
            })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    @staticmethod
    def __backup_config_dir():
        Log.info("Creating backup for older csm configurations")
        backup_dirname = \
            f"{const.CSM_ETC_DIR}_{str(datetime.now()).replace(' ','T').split('.')[0]}_bkp"
        Setup._run_cmd(f"mv {const.CSM_ETC_DIR} {backup_dirname}")
        if os.path.exists(const.CSM_WEB_DIST_ENV_FILE_PATH):
            Setup._run_cmd(f"cp {const.CSM_WEB_DIST_ENV_FILE_PATH} {backup_dirname}")
        return backup_dirname

    @staticmethod
    def __restore_backup_config(backup_dirname):
        Log.info(f"Restoring backedup config data {backup_dirname}")
        backup_index = f"{const.CSM_GLOBAL_INDEX}_BACKUP"
        backup_url = f"yaml://{backup_dirname}/{const.CSM_CONF_FILE_NAME}"
        Conf.load(backup_index, backup_url)
        Conf.copy(backup_index, const.CSM_GLOBAL_INDEX, Conf.get_keys(backup_index))
        Conf.save(const.CSM_GLOBAL_INDEX)

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        self.store_encrypted_password()
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)
