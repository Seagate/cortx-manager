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
import aiohttp
import traceback
from cortx.utils.validator.v_consul import ConsulV
from aiohttp.client_exceptions import ClientConnectionError
from cortx.utils.log import Log
from cortx.utils.validator.error import VError
from csm.core.blogic import const
from csm.common.errors import CsmSetupError, ResourceExist
from csm.common.service_urls import ServiceUrls
from csm.common.conf import Security
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.validator.v_confkeys import ConfKeysV
client = None


class Setup:
    """Base class for csm_setup operations."""

    def __init__(self):
        """Setup init."""
        self._user = None
        self._uid = self._gid = -1
        self._setup_info = dict()
        self._is_env_vm = False
        self._is_env_dev = False
        self.machine_id = Conf.machine_id
        self.conf_store_keys = {}

    @staticmethod
    def _set_csm_conf_path():
        conf_path = Conf.get(const.CONSUMER_INDEX, const.CONFIG_STORAGE_DIR_KEY,
                                                     const.CORTX_CONFIG_DIR)
        conf_path = os.path.join(conf_path, const.NON_ROOT_USER)
        if not os.path.exists(conf_path):
            os.makedirs(conf_path, exist_ok=True)
        Log.info(f"Setting Config saving path:{conf_path} from confstore")
        return conf_path

    @staticmethod
    def get_consul_config():
        result : bool = False
        secret =  Conf.get(const.CONSUMER_INDEX, const.CONSUL_SECRET_KEY)
        protocol, host, port, consul_endpoint = '','','',''
        count_endpoints : str = Conf.get(const.CONSUMER_INDEX,
            const.CONSUL_NUM_ENDPOINTS_KEY)
        try:
            count_endpoints = int(count_endpoints)
        except ValueError:
            raise CsmSetupError("Consul num_endpoints value is not a valid"
                " integer.")
        for count in range(count_endpoints):
            endpoint = Conf.get(const.CONSUMER_INDEX,
                f'{const.CONSUL_ENDPOINTS_KEY}[{count}]')
            if endpoint:
                protocol, host, port = ServiceUrls.parse_url(endpoint)
                if protocol == "https" or protocol == "http":
                    result = True
                    consul_endpoint = endpoint
                    Log.info(f"Fetching consul endpoint : {consul_endpoint}")
                    break
        if not result:
            raise CsmSetupError("Consul endpoint not found.")
        return protocol, host, port, secret, consul_endpoint

    @staticmethod
    def load_csm_config_indices():
        Log.info("Loading CSM configuration")
        set_config_flag = False
        _, consul_host, consul_port, _, _ = Setup.get_consul_config()
        if consul_host and consul_port:
            try:
                ConsulV().validate_service_status(consul_host,consul_port)
                Conf.load(const.CSM_GLOBAL_INDEX,
                        f"consul://{consul_host}:{consul_port}/{const.CSM_CONF_BASE}")
                Conf.load(const.DATABASE_INDEX,
                        f"consul://{consul_host}:{consul_port}/{const.DATABASE_CONF_BASE}")
                set_config_flag = True
            except VError as ve:
                Log.error(f"Unable to fetch the configurations from consul: {ve}")
                raise CsmSetupError("Unable to fetch the configurations")

        if not set_config_flag:
            config_path = Setup._set_csm_conf_path()
            Log.info(f"Setting CSM configuration to local storage: {config_path}")
            Conf.load(const.CSM_GLOBAL_INDEX,
                    f"yaml://{config_path}/{const.CSM_CONF_FILE_NAME}")
            Conf.load(const.DATABASE_INDEX,
                    f"yaml://{config_path}/{const.DB_CONF_FILE_NAME}")
            set_config_flag = True

    @staticmethod
    def copy_base_configs():
        Log.info("Copying Csm base configurations to destination indices")
        Conf.load("CSM_SOURCE_CONF_INDEX",f"yaml://{const.CSM_SOURCE_CONF}")
        Conf.load("DATABASE_SOURCE_CONF_INDEX",f"yaml://{const.DB_SOURCE_CONF}")
        Conf.copy("CSM_SOURCE_CONF_INDEX", const.CSM_GLOBAL_INDEX)
        Conf.copy("DATABASE_SOURCE_CONF_INDEX", const.DATABASE_INDEX)

    @staticmethod
    def load_default_config():
        """Load default configurations for csm."""
        # Load general default configurations for csm.
        Conf.load(const.CSM_DEFAULT_CONF_INDEX,
                        f"yaml://{const.CSM_DEFAULT_CONF}")
        # Load deafult db related configurations for csm.
        Conf.load(const.CSM_DEFAULT_DB_CONF_INDEX,
                        f"yaml://{const.CSM_DEFAULT_DB}")

    @staticmethod
    async def request(url, method, json=None):
        """
        Call DB for Executing the Given API.
        :param url: URI for Connection.
        :param method: API Method.
        :return: Response Object.
        """
        if not json:
            json = dict()
        try:
            async with aiohttp.ClientSession(headers={}) as session:
                async with session.request(method=method.lower(), url=url,
                                           json=json) as response:
                    return await response.text(), response.headers, response.status
        except ClientConnectionError as e:
            Log.error(f"Connection to URI {url} Failed: {e}")
        except Exception as e:
            Log.error(f"Connection to Db Failed. {traceback.format_exc()}")
            raise CsmSetupError(f"Connection to Db Failed. {e}")

    @staticmethod
    async def erase_index(collection, url, method, payload=None):
        Log.info(f"Url: {url}")
        try:
            response, _, status = await Setup.request(url, method, payload)
            if status != 200:
                Log.error(f"Unable to delete collection: {collection}")
                Log.error(f"Response: {response}")
                Log.error(f"Status Code: {status}")
                return None
        except Exception as e:
            Log.warn(f"Failed at deleting for {collection}")
            Log.warn(f"{e}")
        Log.info(f"Index {collection} Deleted.")

    @staticmethod
    def _validate_conf_store_keys(index, keylist=None):
        if not keylist:
            raise CsmSetupError("Keylist should not be empty")
        if not isinstance(keylist, list):
            raise CsmSetupError("Keylist should be kind of list")
        Log.info(f"Validating confstore keys: {keylist}")
        ConfKeysV().validate("exists", index, keylist)

    async def _create_cluster_admin(self, force_action=False):
        """
        Create Cluster admin using CSM User managment.
        Username, Password, Email will be obtaineed from Confstore.
        """
        from csm.core.services.users import CsmUserService, UserManager
        from cortx.utils.data.db.db_provider import DataBaseProvider, GeneralConfig
        from csm.core.controllers.validators import PasswordValidator, UserNameValidator
        Log.info("Creating cluster admin account")
        cluster_admin_user = Conf.get(const.CONSUMER_INDEX,
                                    const.CSM_AGENT_MGMT_ADMIN_KEY)
        cluster_admin_secret = Conf.get(const.CONSUMER_INDEX,
                                    const.CSM_AGENT_MGMT_SECRET_KEY)
        cluster_admin_emailid = Conf.get(const.CONSUMER_INDEX,
                                    const.CSM_AGENT_EMAIL_KEY)
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY)
        decryption_key = Conf.get(const.CSM_GLOBAL_INDEX,const.KEY_DECRYPTION)
        if not (cluster_admin_user or cluster_admin_secret or cluster_admin_emailid):
            raise CsmSetupError("Cluster admin details  not obtainer from confstore")
        Log.info("Set Cortx admin credentials in config")
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_USER,cluster_admin_user)
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_SECRET,cluster_admin_secret)
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_EMAIL,cluster_admin_emailid)
        cluster_admin_secret = Security.decrypt(cluster_admin_secret,
            cluster_id, decryption_key)
        UserNameValidator()(cluster_admin_user)
        PasswordValidator()(cluster_admin_secret)

        Conf.load(const.DB_DICT_INDEX,'dict:{"k":"v"}')
        Conf.copy(const.DATABASE_INDEX,const.DB_DICT_INDEX)
        db_config_dict = {
            'databases':Conf.get(const.DB_DICT_INDEX,'databases'),
            'models': Conf.get(const.DB_DICT_INDEX,'models')
        }
        conf = GeneralConfig(db_config_dict)
        conf['databases']["consul_db"]["config"][const.PORT] = int(
                    conf['databases']["consul_db"]["config"][const.PORT])
        db = DataBaseProvider(conf)
        usr_mngr = UserManager(db)
        usr_service = CsmUserService(usr_mngr)
        if (not force_action) and \
            (await usr_service.validate_cluster_admin_create(cluster_admin_user)):
            Log.console("WARNING: Cortx cluster admin already created.\n"
                        "Please use '-f' option to create admin user forcefully.")
            return None

        if force_action and await usr_mngr.get(cluster_admin_user):
            Log.info(f"Removing current user: {cluster_admin_user}")
            await usr_mngr.delete(cluster_admin_user)

        Log.info(f"Creating cluster admin: {cluster_admin_user}")
        try:
            await usr_service.create_cluster_admin(cluster_admin_user,
                                                cluster_admin_secret,
                                                cluster_admin_emailid)
        except ResourceExist:
            Log.error(f"Cluster admin already exists: {cluster_admin_user}")

    @staticmethod
    def setup_logs_init():
        log_path = Setup.get_csm_log_path()
        Log.init(service_name = const.CSM_SETUP_CMD, log_path = log_path, level=const.LOG_LEVEL,
                console_output=True)

    @staticmethod
    def get_csm_log_path():
        log_path = Conf.get(const.CONSUMER_INDEX, const.CORTX_LOG_PATH_KEY)
        if Conf.machine_id is not None:
            machine_id = Conf.machine_id
            csm_machine_log_path = f"{log_path}/{const.CSM_COMPONENT_NAME}/{machine_id}"
        else:
            csm_machine_log_path = f"{log_path}/{const.CSM_COMPONENT_NAME}"
        return csm_machine_log_path

class CsmSetup(Setup):
    def __init__(self):
        """Csm Setup initialization."""
        super(CsmSetup, self).__init__()
        self._replacement_node_flag = os.environ.get("REPLACEMENT_NODE") == "true"
        if self._replacement_node_flag:
            Log.info("REPLACEMENT_NODE flag is set")
