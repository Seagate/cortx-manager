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
import ldap
from ldap.ldapobject import SimpleLDAPObject
from aiohttp.client_exceptions import ClientConnectionError
from cortx.utils.log import Log
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_path import PathV
from cortx.utils.validator.v_pkg import PkgV
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from csm.common.errors import CsmSetupError, InvalidRequest, ResourceExist
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
        self._ldap_conn = None
        self.machine_id = Conf.machine_id
        self.conf_store_keys = {}

    def _copy_skeleton_configs(self):
        Log.info(f"Copying Csm config skeletons to {self.config_path}")
        Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF} {self.config_path}")
        Setup._run_cmd(f"cp -rn {const.DB_SOURCE_CONF} {self.config_path}")

    def _copy_base_configs(self):
        Log.info(f"Copying Csm config skeletons to Consul")
        Conf.load("CSM_SOURCE_CONF_INDEX",f"yaml://{const.CSM_SOURCE_CONF}")
        Conf.load("DATABASE_SOURCE_CONF_INDEX",f"yaml://{const.DB_SOURCE_CONF}")
        Conf.copy("CSM_SOURCE_CONF_INDEX", const.CSM_GLOBAL_INDEX)
        Conf.copy("DATABASE_SOURCE_CONF_INDEX", const.DATABASE_INDEX)

    def _set_csm_conf_path(self):
        conf_path = Conf.get(const.CONSUMER_INDEX, const.CONFIG_STORAGE_DIR_KEY,
                                                     const.CORTX_CONFIG_DIR)
        conf_path = os.path.join(conf_path, const.NON_ROOT_USER)
        if not os.path.exists(conf_path):
            os.makedirs(conf_path, exist_ok=True)
        Log.info(f"Setting Config saving path:{conf_path} from confstore")
        return conf_path

    def _get_consul_path(self):
        endpoint_list = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ENDPOINTS_KEY)
        secret =  Conf.get(const.CONSUMER_INDEX, const.CONSUL_SECRET_KEY)
        if not endpoint_list:
            raise CsmSetupError("Endpoints not found")
        for each_endpoint in endpoint_list:
            if 'http' in each_endpoint:
                protocol, host, port = self._parse_endpoints(each_endpoint)
                Log.info(f"Fetching consul endpoint : {each_endpoint}")
                return protocol, [host], port, secret, each_endpoint

    def execute_web_and_cli(self,config_url,  service_list, phase_name):
        self._setup_rpm_map = {
                            "agent":"cortx-csm_agent",
                            "web":"cortx-csm_web",
                            "cli":"cortx-cli"
                        }

        if "web" in service_list:
            Log.info("~~~Validate Web rpm and Csm-web-Setup executable~~~")
            # Csm_web_setup will internally execute cli_setup if CLI RPM installed
            try:
                PkgV().validate("rpms", [self._setup_rpm_map.get("web")])
                PathV().validate("exists" ,[f"link:/usr/bin/csm_web_setup"])
                Log.info(f"{self._setup_rpm_map.get('web')} installed")
            except VError as ve:
                Log.warn(f"{self._setup_rpm_map.get('web')} not installed")
                raise CsmSetupError(f"{self._setup_rpm_map.get('web')} not installed.")

            Log.info("~~~Executing Csm-web-Setup~~~")
            Setup._run_cmd(f"csm_web_setup {phase_name} --config {config_url}")

        if "cli" in service_list and "web" not in service_list:
            #Execute only cli-setup
            Log.info("~~~Validate Cli rpm and Cli-Setup executable~~~")
            try:
                PkgV().validate("rpms", [self._setup_rpm_map.get("cli")])
                PathV().validate("exists" ,[f"link:/usr/bin/cli_setup"])
                Log.info(f"{self._setup_rpm_map.get('cli')} installed")
            except VError as ve:
                Log.warn(f"{self._setup_rpm_map.get('cli')} not installed")
                raise CsmSetupError(f"{self._setup_rpm_map.get('cli')} not installed.")

            Log.info("~~~Executing Cli-Setup~~~")
            Setup._run_cmd(f"cli_setup {phase_name} --config {config_url}")

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

    def _set_deployment_mode(self):
        """
        This Method will set a deployment Mode according to env_type.
        :return:
        """
        self._get_setup_info()
        self._set_service_user()
        if self._setup_info[const.NODE_TYPE] in [const.VM, const.VIRTUAL]:
            Log.info("Running Csm Setup for VM Environment Mode.")
            self._is_env_vm = True

        if Conf.get(const.CONSUMER_INDEX, const.KEY_DEPLOYMENT_MODE) == const.DEV:
            Log.info("Running Csm Setup for Dev Mode.")
            self._is_env_dev = True

    def _set_service_user(self):
        """
        This Method will set the username for service user to Self._user
        :return:
        """
        self._user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CSM_USER])

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
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_SECRET, cluster_admin_secret)
        Conf.set(const.CSM_GLOBAL_INDEX,const.CLUSTER_ADMIN_EMAIL, cluster_admin_emailid)
        cluster_admin_secret = self._decrypt_secret(cluster_admin_secret, self.cluster_id,
                                                Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.S3_PASSWORD_DECRYPTION_KEY))
        ldap_csm_admin_secret = Conf.get(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_PASSWORD)

        UserNameValidator()(cluster_admin_user)
        PasswordValidator()(cluster_admin_secret)
        Conf.load('db_dict_index','dict:{}')
        Conf.copy(const.DATABASE_INDEX,'db_dict_index')
        db_config_dict = {
            'databases':Conf.get('db_dict_index','databases'),
            'models': Conf.get('db_dict_index','models')
        }
        del db_config_dict["databases"]["consul_db"]["config"]["hosts_count"]
        del db_config_dict["databases"]["openldap"]["config"]["hosts_count"]
        conf = GeneralConfig(db_config_dict)
        conf['databases']["openldap"]["config"][const.PORT] = int(
                    conf['databases']["openldap"]["config"][const.PORT])
        conf['databases']["openldap"]["config"]["login"] = Conf.get(const.DATABASE_INDEX,
                                             const.DB_OPENLDAP_CONFIG_LOGIN)
        conf['databases']["openldap"]["config"]["password"] = \
                            self._decrypt_secret(ldap_csm_admin_secret,
                                                self.cluster_id,
                                                Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.S3_PASSWORD_DECRYPTION_KEY))

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

    def _is_user_exist(self):
        """
        Check if user exists
        """
        try:
            u = pwd.getpwnam(self._user)
            self._uid = u.pw_uid
            self._gid = u.pw_gid
            return True
        except KeyError as err:
            return False

    def _get_setup_info(self):
        """
        Return Setup Info from Conf Store
        :return:
        """
        self._setup_info = {const.NODE_TYPE: "", const.STORAGE_TYPE: ""}
        self._setup_info[const.NODE_TYPE] = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_SERVER_NODE_TYPE])
        enclosure_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_ENCLOSURE_ID])
        storage_type_key = f"{const.STORAGE_ENCL}>{enclosure_id}>{const.TYPE}"
        self._validate_conf_store_keys(const.CONSUMER_INDEX, [storage_type_key])
        self._setup_info[const.STORAGE_TYPE] = Conf.get(const.CONSUMER_INDEX, storage_type_key)

    @staticmethod
    def _get_machine_id():
        """
        Obtains current minion id. If it cannot be obtained, returns default node #1 id.
        """
        Log.info("Fetching Machine Id.")
        cmd = "cat /etc/machine-id"
        proc_obj = SimpleProcess(cmd)
        machine_id, _err, _returncode = proc_obj.run()
        if _returncode != 0:
            raise CsmSetupError('Unable to obtain current machine id.')
        return (machine_id.decode("utf-8")).replace("\n", "")

    @staticmethod
    def _is_group_exist(user_group):
        """
        Check if user group exists
        """
        try:
            Log.debug(f"Check if user group {user_group} exists.")
            grp.getgrnam(user_group)
            return True
        except KeyError as err:
            return False

    def _check_if_dir_exist_remote_host(self, dir, host):
        try:
            process = SimpleProcess("ssh "+ host +" ls "+ dir)
            stdout, stderr, rc = process.run()
        except Exception as e:
            Log.warn(f"Error in command execution : {e}")
        if stderr:
            Log.warn(stderr)
        if rc == 0:
            return True

    def _create_ssh_config(self, path, private_key):
        ssh_config = '''Host *
    User {user}
    UserKnownHostsFile /dev/null
    StrictHostKeyChecking no
    IdentityFile {private_key}
    IdentitiesOnly yes
    LogLevel ERROR'''.format(user=self._user, private_key=private_key )
        try:
            Log.info(f"Writing ssh config {ssh_config} to file {path}")
            with open(path, "w") as fh:
                fh.write(ssh_config)
        except OSError as err:
            Log.error(f"Error in writing ssh config: {err}")
            if err.errno != errno.EEXIST: raise


    def _config_user_permission_unset(self, bundle_path):
        """
        Unset user permission
        """
        Log.info("Unset User Permission")
        Setup._run_cmd("rm -rf " + const.CSM_TMP_FILE_CACHE_DIR)
        Setup._run_cmd("rm -rf " + bundle_path)
        Setup._run_cmd("rm -rf " + const.CSM_PIDFILE_PATH)

    def _decrypt_secret(self, secret, cluster_id, decryption_key):
        Log.info("Fetching LDAP root user password from Conf Store.")
        try:
            cipher_key = Cipher.generate_key(cluster_id,decryption_key)
        except KvError as error:
            Log.error(f"Failed to Fetch keys from Conf store. {error}")
            return None
        except Exception as e:
            Log.error(f"{e}")
            return None
        try:
            ldap_root_decrypted_value = Cipher.decrypt(cipher_key,
                                                secret.encode("utf-8"))
            return ldap_root_decrypted_value.decode('utf-8')
        except CipherInvalidToken as error:
            Log.error(f"Decryption for LDAP root user password Failed. {error}")
            raise CipherInvalidToken(f"Decryption for LDAP root user password Failed. {error}")

    def _fetch_ldap_root_user(self):
        Log.info("Fetching LDAP root user from Conf Store.")
        try:
            ldap_root_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_ROOT_LDAP_USER])
        except KvError as error:
            Log.error(f"Failed to Fetch keys from Conf store. {error}")
            return None
        except Exception as e:
            Log.error(f"{e}")
            return None
        return ldap_root_user

    def _connect_to_ldap_server(self, ldap_url, bind_dn, ldappasswd):
        """
        Establish connection to ldap server.
        """
        from ldap import initialize, VERSION3, OPT_REFERRALS
        Log.info("Setting up Ldap connection")
        self._ldap_conn = initialize(ldap_url)
        self._ldap_conn.protocol_version = VERSION3
        self._ldap_conn.set_option(OPT_REFERRALS, 0)
        self._ldap_conn.simple_bind_s(bind_dn, ldappasswd)

    def _disconnect_from_ldap(self):
        """
        Disconnects from ldap.
        """
        Log.info("Closing Ldap connection")
        self._ldap_conn.unbind_s()
        self._ldap_conn = None

    def _delete_user_data(self, bind_dn, ldappasswd, users_dn):
        """
        Delete data entries from ldap.
        """
        try:
            self._connect_to_ldap_server(Setup._get_ldap_url(), bind_dn, ldappasswd)
            try:
                self._ldap_delete_recursive(self._ldap_conn, users_dn)
            except ldap.NO_SUCH_OBJECT:
            # If no entries found in ldap for given dn
                pass
            self._disconnect_from_ldap()
        except Exception as e:
            if self._ldap_conn:
                self._disconnect_from_ldap()
            Log.error(f'ERROR: Failed to delete ldap data, error: {str(e)}')
            raise CsmSetupError(f'Failed to delete ldap data, error: {str(e)}')

    def _ldap_delete_recursive(self, ldap_conn: SimpleLDAPObject, users_dn: str):
        """
        Delete all objects and its subordinate entries from ldap.
        """
        Log.info(f'Deleting all entries from {users_dn}')
        l_search = ldap_conn.search_s(users_dn, ldap.SCOPE_ONELEVEL)
        for dn, _ in l_search:
            if not dn == users_dn:
                self._ldap_delete_recursive(ldap_conn, dn)
                ldap_conn.delete_s(dn)
    @staticmethod
    def _get_ldap_url():
        """
        Return ldap url
        ldap endpoint and port will be read from database conf
        """
        ldap_hosts_count = int(Conf.get(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_HOSTS_COUNT))
        for each_ldap_host in range(ldap_hosts_count):
            ldap_endpoint = Conf.get(const.DATABASE_INDEX,
                        f'{const.DB_OPENLDAP_CONFIG_HOSTS}[{each_ldap_host}]')
        ldap_port = Conf.get(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_PORT)
        ldap_url = f"ldap://{ldap_endpoint}:{ldap_port}/"
        return ldap_url

    @staticmethod
    def _get_ldap_server_url():
        ldap_server_url_list = []
        ldap_port = Conf.get(const.DATABASE_INDEX, const.DB_OPENLDAP_CONFIG_PORT)
        for each_count in range(int(Conf.get(const.DATABASE_INDEX, const.OPEN_LDAP_SERVERS_COUNT))):
            ldap_server = Conf.get(const.DATABASE_INDEX, f'{const.OPEN_LDAP_SERVERS}[{each_count}]')
            ldap_server_url_list.append(f"ldap://{ldap_server}:{ldap_port}/")
        return ldap_server_url_list

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

    class Config:
        """
        Action for csm config
            create: Copy configuraion file
            load: Load configuraion file
            reset: Reset configuraion file
            delete: Delete configuration file
        """

        @staticmethod
        def load():
            Log.info("Loading config")
            csm_conf_target_path = os.path.join(const.CSM_CONF_PATH,
                                                const.CSM_CONF_FILE_NAME)
            if not os.path.exists(csm_conf_target_path):
                Log.error(f"{const.CSM_CONF_FILE_NAME} file is missing for csm setup")
                raise CsmSetupError(f"{const.CSM_CONF_FILE_NAME} file is missing for csm setup")
            Conf.load(const.CSM_GLOBAL_INDEX, f"yaml://{csm_conf_target_path}")
            Log.info("Loading database config")
            Setup.Config.load_db()

        @staticmethod
        def load_db():
            Log.info("Loading databse config")
            db_conf_target_path = os.path.join(const.CSM_CONF_PATH, const.DB_CONF_FILE_NAME)
            if not os.path.exists(db_conf_target_path):
                Log.error("%s file is missing for csm setup" %const.DB_CONF_FILE_NAME)
                raise CsmSetupError("%s file is missing for csm setup" %const.DB_CONF_FILE_NAME)
            Conf.load(const.DATABASE_INDEX, f"yaml://{db_conf_target_path}")

        @staticmethod
        def delete():
            Log.info("Delete config")
            Setup._run_cmd("rm -rf " + const.CSM_CONF_PATH)

        @staticmethod
        def reset():
            Log.info("Reset config")
            os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
            Setup._run_cmd("cp -rf " +const.CSM_SOURCE_CONF_PATH+ " " +const.ETC_PATH)

    def _log_cleanup(self):
        """
        Delete all logs
        """
        Log.info("Delete all logs")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        Setup._run_cmd("rm -rf " +log_path)

    class ConfigServer:
        """
        Manage Csm service
            stop: Stop csm service
            restart: restart csm service
            reload: reload systemd deamon
        """

        @staticmethod
        def stop():
            _proc = SimpleProcess("systemctl is-active csm_agent")
            _output_agent, _err_agent, _rc_agent = _proc.run(universal_newlines=True)
            _proc = SimpleProcess("systemctl is-active csm_web")
            _output_web, _err_web, _rc_web = _proc.run(universal_newlines=True)
            if _rc_agent == 0:
                _proc = SimpleProcess("systemctl stop csm_agent")
                _output_agent, _err_agent, _rc_agent = _proc.run(universal_newlines=True)
            if _rc_web == 0:
                _proc = SimpleProcess("systemctl stop csm_web")
                _output_agent, _err_agent, _rc_agent = _proc.run(universal_newlines=True)

        @staticmethod
        def reload():
            Setup._run_cmd("systemctl daemon-reload")

        @staticmethod
        def restart():
            _proc = SimpleProcess("systemctl is-active csm_agent")
            _output_agent, _err_agent, _rc_agent = _proc.run(universal_newlines=True)
            _proc = SimpleProcess("systemctl is-active csm_web")
            _output_web, _err_web, _rc_web = _proc.run(universal_newlines=True)
            if _rc_agent == 0:
                Setup._run_cmd("systemctl restart csm_agent")
            if _rc_web == 0:
                Setup._run_cmd("systemctl restart csm_web")

    def _configure_system_auto_restart(self):
        """
        Check's System Installation Type an dUpdate the Service File
        Accordingly.
        :return: None
        """
        Log.info("Configuring System Auto restart")
        is_auto_restart_required = list()
        if self._setup_info:
            for each_key in self._setup_info:
                comparison_data = const.EDGE_INSTALL_TYPE.get(each_key, None)
                #Check Key Exists:
                if comparison_data is None:
                    Log.warn(f"Edge Installation missing key {each_key}")
                    continue
                if isinstance(comparison_data, list):
                    if self._setup_info[each_key] in comparison_data:
                        is_auto_restart_required.append(False)
                    else:
                        is_auto_restart_required.append(True)
                elif self._setup_info[each_key] == comparison_data:
                    is_auto_restart_required.append(False)
                else:
                    is_auto_restart_required.append(True)
        else:
            Log.warn("Setup info does not exist.")
            is_auto_restart_required.append(True)
        if any(is_auto_restart_required):
            Log.debug("Updating All setup file for Auto Restart on "
                             "Failure")
            Setup._update_systemd_conf("#< RESTART_OPTION >",
                                      "Restart=on-failure")
            Setup._run_cmd("systemctl daemon-reload")

    @staticmethod
    def is_k8s_env() -> bool:
        """
        Check if systemd should be used for the current set up.

        :returns: True if systemd should be used.
        """
        env_type = Conf.get(const.CONSUMER_INDEX, const.ENV_TYPE_KEY, None)
        return env_type == const.K8S

    @staticmethod
    def _copy_systemd_configuration():
        if Setup.is_k8s_env:
            Log.warn('SystemD is not used in this environment and will not be set up')
            return
        Setup._run_cmd(f"cp {const.CSM_AGENT_SERVICE_SRC_PATH} {const.CSM_AGENT_SERVICE_FILE_PATH}")
        Setup._run_cmd(f"cp {const.CSM_WEB_SERVICE_SRC_PATH} {const.CSM_WEB_SERVICE_FILE_PATH}")

    @staticmethod
    def _update_systemd_conf(key, value):
        """
        Update CSM Files Depending on Job Type of Setup.
        """
        if Setup.is_k8s_env:
            Log.warn('SystemD is not used in this environment and will not be updated')
            return
        Log.info(f"Update file for {key}:{value}")
        for each_file in const.CSM_FILES:
            service_file_data = Text(each_file).load()
            if not service_file_data:
                Log.warn(f"File {each_file} not updated.")
                continue
            data = service_file_data.replace(key, value)
            Text(each_file).dump(data)

# TODO: Divide changes in backend and frontend
# TODO: Optimise use of args for like product, force, component
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

    def reset(self, args):
        try:
            self._verify_args(args)
            self.Config.load()
            self.ConfigServer.stop()
            self._log_cleanup()
            self._config_user_permission(reset=True)
            self.Config.delete()
            self._config_user(reset=True)
        except Exception as e:
            Log.error(f"csm_setup reset failed. Error: {e} - {str(traceback.print_exc())}")
            raise CsmSetupError(f"csm_setup reset failed. Error: {e} - {str(traceback.print_exc())}")
