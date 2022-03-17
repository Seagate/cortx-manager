# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

from csm.core.providers.providers import Response
from csm.core.blogic import const
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.log import Log
from cortx.utils.conf_store import Conf
from csm.conf.setup import Setup, CsmSetupError
from cortx.utils.kv_store.error import KvError

class Upgrade(Setup):
    """
    Perform upgrade operations for csm
    """
    def __init__(self):
        super(Upgrade, self).__init__()

    async def execute(self, command):
        Log.info("Performing upgrade and loading config files")
        try:
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            self.load_csm_config_indices()
            self.load_default_config()
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        services = command.options.get("services")
        if 'agent' in services or 'all' in services:
            services = ["agent"]
        else:
            raise CsmSetupError(f"Provided services are unsupported:{services}")
        self.upgrade()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def upgrade(self):
        """
        Perform upgrade
        """
        Log.info("Preparing for upgrade.")
        self._update_general_config(const.CSM_DEFAULT_CONF_INDEX, const.CSM_GLOBAL_INDEX)
        self._update_db_config(const.CSM_DEFAULT_DB_CONF_INDEX, const.DATABASE_INDEX)

    def _update_general_config(self, default_index, current_index):
        Log.info("Updating general configurations.")
        self._update(default_index, current_index)

    def _update_db_config(self, default_index, current_index):
        Log.info("Updating database configurations.")
        self._update(default_index, current_index)

    def _update(self, default_index, current_index):
        """
        Update configurations based default config.
        :param default_index:default configutions for specific version.
        :param current_index:current configutions of deployed version.
        :returns
        """
        default_keys =  Conf.get_keys(default_index)
        for key in default_keys:
            default_value = Conf.get(default_index, key)
            # default_val is empty i,e expecting value from conf_store
            if not default_value:
                continue
            # Add key-val pair to current index if missing otherwise
            # Update Key-val pair from current index based on deafult values
            current_value = Conf.get(current_index, key)
            if current_value:
                if default_value == current_value:
                    continue
                else:
                    # handle case if values of config mismatched
                    self._update_current_config(key, default_index, current_index)
            else:
                Conf.set(current_index, key, default_value)

    def _update_current_config(self, key, default_index, current_index):
        """
        Update current configurtion based on default/prvs config as follows:
        If current config value is diffrent from default config value and:
        1.previous value is not present -> pass
        2.previous value is present and (previous val == current val) -> set previous to default
        3.previous value is present and (previous val != current val) -> pass
        :param default_index:default configutions for specific version.
        :param current_index:current configutions of deployed version.
        :returns
        """
        previous_key = self._previous_key(key)
        previous_value = Conf.get(default_index, previous_key)
        if previous_value:
            current_value = Conf.get(current_index, key)
            default_value = Conf.get(default_index, key)
            if previous_value == current_value:
                Conf.set(current_index, key, default_value)

    def _previous_key(self, key):
        """
        Form previous key from given key.
        if key is 'DEBUG>enabled'
        previous_key will be 'DEBUG>pre_enabled'
        """
        keys = key.rsplit('>', 1)
        if len(keys)==1:
            return f"pre_{key}"
        return f"{keys[0]}>pre_{keys[-1]}"
