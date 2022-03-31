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
import pwd
import grp
import errno
import aiohttp
from cortx.utils.validator.v_consul import ConsulV
from aiohttp.client_exceptions import ClientConnectionError
from cortx.utils.log import Log
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_path import PathV
from cortx.utils.validator.v_pkg import PkgV
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from csm.common.errors import CsmSetupError, ResourceExist
import traceback
from csm.common.payload import Text
from cortx.utils.security.cipher import Cipher, CipherInvalidToken
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.v_confkeys import ConfKeysV
client = None


class Setup:
    def __init__(self):
        self._user = None
        self._uid = self._gid = -1
        self._setup_info = dict()
        self._is_env_vm = False
        self._is_env_dev = False
        self.machine_id = Conf.machine_id
        self.conf_store_keys = {}

    def _copy_skeleton_configs(self):
        Log.info(f"Copying Csm config skeletons to {self.config_path}")
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF} {self.config_path}")
        Setup._run_cmd(f"cp -rn {const.DB_SOURCE_CONF} {self.config_path}")

    def _set_csm_conf_path(self):
        conf_path = Conf.get(const.CONSUMER_INDEX, const.CONFIG_STORAGE_DIR_KEY,
                                                     const.CORTX_CONFIG_DIR)
        conf_path = os.path.join(conf_path, const.NON_ROOT_USER)
        if not os.path.exists(conf_path):
            os.makedirs(conf_path, exist_ok=True)
        Log.info(f"Setting Config saving path:{conf_path} from confstore")
        return conf_path

    def _get_consul_config(self):
        protocol, host, port, secret, each_endpoint = '','','','',''
        endpoint_list = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ENDPOINTS_KEY)
        secret =  Conf.get(const.CONSUMER_INDEX, const.CONSUL_SECRET_KEY)
        for each_endpoint in endpoint_list:
            if 'http' in each_endpoint:
                protocol, host, port = self._parse_endpoints(each_endpoint)
                Log.info(f"Fetching consul endpoint : {each_endpoint}")
                break
        return protocol, host, port, secret, each_endpoint

    def load_csm_config_indices(self):
        set_config_flag = False
        protocol, consul_host, consul_port, secret, endpoint = self._get_consul_config()
        if consul_host and consul_port:
            try:
                ConsulV().validate_service_status(consul_host,consul_port)
                Log.info("Setting CSM configuration to consul")
                Conf.load(const.CSM_GLOBAL_INDEX,
                        f"consul://{consul_host}:{consul_port}/{const.CSM_CONF_BASE}")
                Conf.load(const.DATABASE_INDEX,
                        f"consul://{consul_host}:{consul_port}/{const.DATABASE_CONF_BASE}")
                set_config_flag = True
            except VError as ve:
                Log.error(f"Unable to fetch the configurations from consul: {ve}")
                raise CsmSetupError("Unable to fetch the configurations")

        if not set_config_flag:
            config_path = self._set_csm_conf_path()
            Log.info(f"Setting CSM configuration to local storage: {config_path}")
            Conf.load(const.CSM_GLOBAL_INDEX,
                    f"yaml://{config_path}/{const.CSM_CONF_FILE_NAME}")
            Conf.load(const.DATABASE_INDEX,
                    f"yaml://{config_path}/{const.DB_CONF_FILE_NAME}")
            set_config_flag = True

    def _copy_base_configs(self):
        Log.info(f"Copying Csm base configurations to destination indices")
        Conf.load("CSM_SOURCE_CONF_INDEX",f"yaml://{const.CSM_SOURCE_CONF}")
        Conf.load("DATABASE_SOURCE_CONF_INDEX",f"yaml://{const.DB_SOURCE_CONF}")
        Conf.copy("CSM_SOURCE_CONF_INDEX", const.CSM_GLOBAL_INDEX)
        Conf.copy("DATABASE_SOURCE_CONF_INDEX", const.DATABASE_INDEX)

    def load_default_config(self):
        """
        Load default configurations for csm.
        """
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
            response, headers, status = await Setup.request(url, method, payload)
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

    @staticmethod
    def _run_cmd(cmd):
        """
        Run command and throw error if cmd failed
        """
        try:
            _err = ""
            Log.info(f"Executing cmd: {cmd}")
            _proc = SimpleProcess(cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            Log.info(f"Output: {_output}, \n Err:{_err}, \n RC:{_rc}")
            if _rc != 0:
                raise
            return _output, _err, _rc
        except Exception as e:
            Log.error(f"Csm setup is failed Error: {e}, {_err}")
            raise CsmSetupError("Csm setup is failed Error: %s %s" %(e,_err))

    def _fetch_csm_user_password(self, decrypt=False):
        """
        This Method Fetches the Password for CSM User from Provisioner.
        :param decrypt:
        :return:
        """
        csm_user_pass = None
        if self._is_env_dev:
            decrypt = False
        Log.info("Fetching CSM User Password from Conf Store.")
        csm_user_pass = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CSM_SECRET])
        if decrypt and csm_user_pass:
            Log.info("Decrypting CSM Password.")
            try:
                cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
                cipher_key = Cipher.generate_key(cluster_id,
                            Conf.get(const.CSM_GLOBAL_INDEX, "CSM>password_decryption_key"))
            except KvError as error:
                Log.error(f"Failed to Fetch Cluster Id. {error}")
                return None
            except Exception as e:
                Log.error(f"{e}")
                return None
            try:
                decrypted_value = Cipher.decrypt(cipher_key,
                                                 csm_user_pass.encode("utf-8"))
                return decrypted_value.decode("utf-8")
            except CipherInvalidToken as error:
                Log.error(f"Decryption for CSM Failed. {error}")
                raise CipherInvalidToken(f"Decryption for CSM Failed. {error}")
        return csm_user_pass

    async def _create_cluster_admin(self, force_action=False):
        '''
        Create Cluster admin using CSM User managment.
        Username, Password, Email will be obtaineed from Confstore
        '''
        from csm.core.services.users import CsmUserService, UserManager
        from cortx.utils.data.db.db_provider import DataBaseProvider, GeneralConfig
        from csm.core.controllers.validators import PasswordValidator, UserNameValidator
        from csm.common.conf import Security
        Log.info("Creating cluster admin account")
        cluster_admin_user = Conf.get(const.CONSUMER_INDEX,
                                    const.CSM_AGENT_MGMT_ADMIN_KEY)
        cluster_admin_secret = Conf.get(const.CONSUMER_INDEX,
                                    const.CSM_AGENT_MGMT_SECRET_KEY)
        cluster_admin_emailid = Conf.get(const.CONSUMER_INDEX,
                                    const.CSM_AGENT_EMAIL_KEY)
        if not (cluster_admin_user or cluster_admin_secret or cluster_admin_emailid):
            raise CsmSetupError("Cluster admin details  not obtainer from confstore")
        Log.info("Set Cortx admin credentials in config")
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_USER,cluster_admin_user)
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_SECRET,cluster_admin_secret)
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_EMAIL,cluster_admin_emailid)
        cluster_admin_secret = self._decrypt_secret(cluster_admin_secret, self.cluster_id,
                                                Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.S3_PASSWORD_DECRYPTION_KEY))
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
        except ResourceExist as ex:
            Log.error(f"Cluster admin already exists: {cluster_admin_user}")

    def _decrypt_secret(self, secret, cluster_id, decryption_key):
        try:
            cipher_key = Cipher.generate_key(cluster_id,decryption_key)
        except KvError as error:
            Log.error(f"Failed to Fetch keys from Conf store. {error}")
            return None
        except Exception as e:
            Log.error(f"{e}")
            return None
        try:
            decrypted_value = Cipher.decrypt(cipher_key,
                                                secret.encode("utf-8"))
            return decrypted_value.decode('utf-8')
        except CipherInvalidToken as error:
            Log.error(f"Secret decryption Failed. {error}")
            raise CipherInvalidToken(f"Secret decryption Failed. {error}")

    def _parse_endpoints(self, url):
        if "://"in url:
            protocol, endpoint = url.split("://")
        else:
            protocol = ''
            endpoint = url
        host, port = endpoint.split(":")
        Log.info(f"Parsing endpoint url:{url} as protocol:{protocol}, host:{host}, port:{port}")
        return protocol, host, port

    def _get_log_path_from_conf_store(self):
        log_path = Conf.get(const.CONSUMER_INDEX, const.CSM_LOG_PATH_KEY, const.CSM_LOG_PATH)
        if log_path and log_path.find(const.CSM_COMPONENT_NAME) == -1:
            log_path = log_path + f"/{const.CSM_COMPONENT_NAME}/"
        return log_path

    def _log_cleanup(self):
        """
        Delete all logs
        """
        Log.info("Delete all logs")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        Setup._run_cmd("rm -rf " +log_path)

class CsmSetup(Setup):
    def __init__(self):
        super(CsmSetup, self).__init__()
        self._replacement_node_flag = os.environ.get("REPLACEMENT_NODE") == "true"
        if self._replacement_node_flag:
            Log.info("REPLACEMENT_NODE flag is set")

    def _verify_args(self, args):
        """
        Verify args for actions
        """
        Log.info(f"Verifying arguments... {args}")
        if "Product" in args.keys() and args["Product"] != "cortx":
            raise Exception("Not implemented for Product %s" %args["Product"])
        if "Component" in args.keys() and args["Component"] != "all":
            raise Exception("Not implemented for Component %s" %args["Component"])
        if "f" in args.keys() and args["f"] is True:
            raise Exception("Not implemented for force action")
