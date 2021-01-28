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
import errno
import shlex
import json
from cortx.utils.log import Log
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from csm.common.errors import CsmSetupError, InvalidRequest
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.common.ha_framework import PcsHAFramework
from csm.common.cluster import Cluster
from csm.core.agent.api import CsmApi
import traceback
from csm.common.payload import Text
from cortx.utils.security.cipher import Cipher, CipherInvalidToken
from csm.conf.uds import UDSConfigGenerator
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kvstore.error import KvError

# try:
#     from salt import client
# except ModuleNotFoundError:
client = None


class InvalidPillarDataError(InvalidRequest):
    pass


class ProvisionerCliError(InvalidRequest):
    pass


class Setup:
    def __init__(self):
        self._user = None
        self._uid = self._gid = -1
        self._setup_info = dict()
        self._is_env_vm = False

    def _set_deployment_mode(self):
        """
        This Method will set a deployment Mode according to env_type.
        :return:
        """
        self._get_setup_info()
        self._set_service_user()
        if self._setup_info[const.NODE_TYPE] == const.VM:
            Log.info("Running Csm Setup for VM Environment Mode.")
            self._is_env_vm = True

    def _set_service_user(self):
        """
        This Method will set the username for service user to Self._user
        :return:
        """
        self._user = Conf.get(const.CONSUMER_INDEX, "system.service-user>name")

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
        if self._is_env_vm:
            decrypt = False
        Log.info("Fetching CSM User Password from Config Store.")
        try:
            # TODO: Need to Change Method for Fetching Csm Credentials.
            csm_user_pass = Conf.get(const.CONSUMER_INDEX,
                                     f"system.service-user>secret")
        except KvError as e:
            Log.error(f"Failed to Fetch Csm Secret {e}")
        if decrypt and csm_user_pass:
            Log.info("Decrypting CSM Password.")
            try:
                cluster_id = Conf.get(const.CONSUMER_INDEX,
                                      f"{const.CLUSTER}>{const.CLUSTER_ID}")
                cipher_key = Cipher.generate_key(cluster_id, "csm")
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
        self._setup_info = {"node_type": "",
                            "storage_type": ""}
        server_nodes = Conf.get(const.CONSUMER_INDEX, "cluster>server_nodes")
        machine_id = Setup._get_machine_id()
        node_type_key = (f"{const.CLUSTER}>{server_nodes.get(machine_id, '')}"
                         f">{const.NODE_TYPE}")
        self._setup_info[const.NODE_TYPE] = Conf.get(const.CONSUMER_INDEX,
                                               node_type_key)
        storage_type_key = (f"{const.STORAGE}>{server_nodes.get(machine_id, '')}"
                         f">{const.TYPE}")
        self._setup_info[const.STORAGE_TYPE] = Conf.get(const.CONSUMER_INDEX,
                                                  storage_type_key)

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

    @staticmethod
    def get_data_from_provisioner_cli(method, output_format="json"):
        try:
            Log.info("Execute proviioner cli cmd: {method} ")
            process = SimpleProcess(f"provisioner {method} --out={output_format}")
            stdout, stderr, rc = process.run()
        except Exception as e:
            Log.error(f"Error in command execution : {e}")
            raise ProvisionerCliError(f"Error in command execution : {e}")
        if stderr:
            raise ProvisionerCliError(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result[const.RET]

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

    def _config_cluster(self, args):
        """
        Instantiation of csm cluster with resources
        Create csm user
        """
        Log.info("Instantiation of csm cluster with resources")
        self._csm_resources = Conf.get(const.CSM_GLOBAL_INDEX, "HA>resources")
        self._csm_ra = {
            "csm_resource_agent": CsmResourceAgent(self._csm_resources)
        }
        self._ha_framework = PcsHAFramework(self._csm_ra)
        self._cluster = Cluster(const.INVENTORY_FILE, self._ha_framework)
        self._cluster.init(args['f'])
        CsmApi.set_cluster(self._cluster)

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
            Setup._update_service_file("#< RESTART_OPTION >",
                                      "Restart=on-failure")
            Setup._run_cmd("systemctl daemon-reload")

    @staticmethod
    def _update_service_file(key, value):
        """
        Update CSM Agent and CSM Web service Files Depending on Job Type of
        Setup.
        """
        Log.info(f"Update service file for {key}:{value}")
        for each_service_file in const.CSM_SERVICE_FILES:
            service_file_data = Text(each_service_file).load()
            if not service_file_data:
                Log.warn(f"File {each_service_file} not updated.")
                continue
            data = service_file_data.replace(key, value)
            Text(each_service_file).dump(data)

# TODO: Devide changes in backend and frontend
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
            UDSConfigGenerator.delete()
        except Exception as e:
            Log.error(f"csm_setup reset failed. Error: {e} - {str(traceback.print_exc())}")
            raise CsmSetupError(f"csm_setup reset failed. Error: {e} - {str(traceback.print_exc())}")
