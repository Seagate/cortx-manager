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
from csm.common.conf import Conf
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from csm.common.errors import CsmSetupError, InvalidRequest
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.common.ha_framework import PcsHAFramework
from csm.common.cluster import Cluster
from csm.core.agent.api import CsmApi
import re
import time
import traceback
import asyncio
from csm.core.blogic.models.alerts import AlertModel
from csm.core.services.alerts import AlertRepository
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.common.payload import Text

# try:
#     from salt import client
# except ModuleNotFoundError:
client = None

class InvalidPillarDataError(InvalidRequest):
    pass
class PillarDataFetchError(InvalidRequest):
    pass

class ProvisionerCliError(InvalidRequest):
    pass


class Setup:
    def __init__(self):
        self._user = const.NON_ROOT_USER
        self._password = crypt.crypt(const.NON_ROOT_USER_PASS, "22")
        self._uid = self._gid = -1
        self._setup_info = dict()

    @staticmethod
    def _run_cmd(cmd):
        """
        Run command and throw error if cmd failed
        """
        try:
            _err = ""
            _proc = SimpleProcess(cmd)
            _output, _err, _rc = _proc.run(universal_newlines=True)
            if _rc != 0:
                raise
            return _output, _err, _rc
        except Exception as e:
            raise CsmSetupError("Csm setup is failed Error: %s %s" %(e,_err))

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

    @staticmethod
    def _is_group_exist(user_group):
        """
        Check if user group exists
        """
        try:
            grp.getgrnam(user_group)
            return True
        except KeyError as err:
            return False

    @staticmethod
    def get_salt_data(method, key):
        try:
            process = SimpleProcess(f"salt-call {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            Log.logger.warn(f"Error in command execution : {e}")
        if stderr:
            Log.logger.warn(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result[const.LOCAL]

    @staticmethod
    def get_salt_data_with_exception(method, key):
        try:
            process = SimpleProcess(f"salt-call {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            raise PillarDataFetchError(f"Error in command execution : {e}")
        if stderr:
            raise PillarDataFetchError(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result[const.LOCAL]

    @staticmethod
    def get_salt_data_faulty_node_uuid(minion_id, method, key):
        try:
            process = SimpleProcess(f"salt {minion_id} {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            raise PillarDataFetchError(f"Error in command execution : {e}")
        if stderr:
            raise PillarDataFetchError(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result[minion_id]

    @staticmethod
    def get_data_from_provisioner_cli(method, output_format="json"):
        try:
            process = SimpleProcess(f"provisioner {method} --out={output_format}")
            stdout, stderr, rc = process.run()
        except Exception as e:
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
            Log.logger.warn(f"Error in command execution : {e}")
        if stderr:
            Log.logger.warn(stderr)
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
            with open(path, "w") as fh:
                fh.write(ssh_config)
        except OSError as err:
            if err.errno != errno.EEXIST: raise

    def _passwordless_ssh(self, home_dir):
        """
        make passwordless ssh to nodes
        """
        Setup._run_cmd("mkdir "+os.path.join(home_dir, const.SSH_DIR))
        cmd = shlex.split("ssh-keygen -N '' -f "+os.path.join(home_dir, const.SSH_PRIVATE_KEY))
        Setup._run_cmd(cmd)
        self._create_ssh_config(os.path.join(home_dir, const.SSH_CONFIG), os.path.join(home_dir, const.SSH_PRIVATE_KEY))
        Setup._run_cmd("cp "+os.path.join(home_dir, const.SSH_PUBLIC_KEY)+" " +
                                                     os.path.join(home_dir, const.SSH_AUTHORIZED_KEY))
        Setup._run_cmd("chown -R "+self._user+":"+self._user+" "+os.path.join(home_dir, const.SSH_DIR))
        Setup._run_cmd("chmod 400 "+os.path.join(const.CSM_USER_HOME, const.SSH_PRIVATE_KEY))

    def _config_user(self, reset=False):
        """
        Check user already exist and create if not exist
        If reset true then delete user
        """
        if not reset:
            if not self._is_user_exist():
                Setup._run_cmd("useradd -d "+const.CSM_USER_HOME+" -p "+self._password+" "+ self._user)
                Setup._run_cmd("usermod -aG wheel " + self._user)
                if not self._is_user_exist():
                    raise CsmSetupError("Unable to create %s user" % self._user)
                node_name = Setup.get_salt_data(const.GRAINS_GET, "id")
                primary = Setup.get_salt_data(const.GRAINS_GET, "roles")
                if ( node_name is None or const.PRIMARY_ROLE in primary):
                    self._passwordless_ssh(const.CSM_USER_HOME)
                nodes = Setup.get_salt_data(const.PILLAR_GET, const.NODE_LIST_KEY)
                if ( primary and const.PRIMARY_ROLE in primary and nodes is not None and len(nodes) > 1 ):
                    nodes.remove(node_name)
                    for node in nodes:
                        if (self._check_if_dir_exist_remote_host(const.CSM_USER_HOME, node)):
                            Setup._run_cmd("scp -pr "+os.path.join(const.CSM_USER_HOME, const.SSH_DIR)+" "+
                                      node+":"+const.CSM_USER_HOME)
                            Setup._run_cmd(" ssh "+node+" chown -R "+self._user+":"+self._user+" "+
                                                 os.path.join(const.CSM_USER_HOME, const.SSH_DIR) )
        else:
            if self._is_user_exist():
                Setup._run_cmd("userdel -r " +self._user)
        if self._is_user_exist() and Setup._is_group_exist(const.HA_CLIENT_GROUP):
            Setup._run_cmd(f"usermod -a -G {const.HA_CLIENT_GROUP}  {self._user}")

    def _config_user_permission_set(self, bundle_path, crt, key):
        """
        Set User Permission
        """
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path")
        os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
        os.makedirs(const.CSM_PIDFILE_PATH, exist_ok=True)
        os.makedirs(log_path, exist_ok=True)
        os.makedirs(bundle_path, exist_ok=True)
        os.makedirs(const.CSM_TMP_FILE_CACHE_DIR, exist_ok=True)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_PATH)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_TMP_FILE_CACHE_DIR)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + bundle_path)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + log_path)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_CONF_PATH)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_PIDFILE_PATH)
        Setup._run_cmd("setfacl -R -b " + const.CSM_USER_HOME)
        Setup._run_cmd("setfacl -m u:" + self._user + ":rwx " + crt)
        Setup._run_cmd("setfacl -m u:" + self._user + ":rwx " + key)

    def _config_user_permission_unset(self, bundle_path):
        """
        Unset user permission
        """
        Setup._run_cmd("rm -rf " + const.CSM_TMP_FILE_CACHE_DIR)
        Setup._run_cmd("rm -rf " + bundle_path)
        Setup._run_cmd("rm -rf " + const.CSM_PIDFILE_PATH)


    def _config_user_permission(self, reset=False):
        """
        Create user and allow permission for csm resources
        """
        bundle_path = Conf.get(const.CSM_GLOBAL_INDEX, "SUPPORT_BUNDLE.bundle_path")
        crt = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS.certificate_path")
        key = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS.private_key_path")
        if not reset:
            self._config_user_permission_set(bundle_path, crt, key)
        else:
            self._config_user_permission_unset(bundle_path)

    class Config:
        """
        Action for csm config
            create: Copy configuraion file
            load: Load configuraion file
            reset: Reset configuraion file
            delete: Delete configuration file
        """

        @staticmethod
        def store_encrypted_password(conf_data):
            # read username's and password's for S3 and RMQ
            open_ldap_credentials = Setup.get_salt_data_with_exception(const.PILLAR_GET, const.OPENLDAP)
            # Edit Current Config File.
            if open_ldap_credentials and type(open_ldap_credentials) is dict:
                conf_data[const.S3][const.LDAP_LOGIN] = open_ldap_credentials.get(
                                                    const.IAM_ADMIN, {}).get(const.USER)
                conf_data[const.S3][const.LDAP_PASSWORD] = open_ldap_credentials.get(
                                                    const.IAM_ADMIN, {}).get(const.SECRET)
            else:
                raise InvalidPillarDataError(f"failed to get pillar data for {const.OPENLDAP}")
            sspl_config = Setup.get_salt_data_with_exception(const.PILLAR_GET, const.SSPL)
            if sspl_config and type(sspl_config) is dict:
                conf_data[const.CHANNEL][const.USERNAME] = sspl_config.get(const.USERNAME)
                conf_data[const.CHANNEL][const.PASSWORD] = sspl_config.get(const.PASSWORD)
            else:
                raise InvalidPillarDataError(f"failed to get pillar data for {const.SSPL}")
            cluster_id =  Setup.get_salt_data_with_exception(const.GRAINS_GET, const.CLUSTER_ID)
            provisioner_data = conf_data[const.PROVISIONER]
            provisioner_data[const.CLUSTER_ID] = cluster_id
            conf_data[const.PROVISIONER] = provisioner_data

        @staticmethod
        def create(args):
            """
            This Function Creates the CSM Conf File on Required Location.
            :return:
            """
            csm_conf_target_path = os.path.join(const.CSM_CONF_PATH, const.CSM_CONF_FILE_NAME)
            csm_conf_path = os.path.join(const.CSM_SOURCE_CONF_PATH, const.CSM_CONF_FILE_NAME)
            # Read Current CSM Config FIle.
            conf_file_data = Yaml(csm_conf_path).load()
            if conf_file_data:
                if args[const.DEBUG]:
                    conf_file_data[const.DEPLOYMENT] = {const.MODE : const.DEV}
                else:
                    Setup.Config.store_encrypted_password(conf_file_data)
                    # Update the Current Config File.
                    Yaml(csm_conf_path).dump(conf_file_data)
                Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")
                if args[const.DEBUG]:
                    Yaml(csm_conf_target_path).dump(conf_file_data)
            else:
                raise CsmSetupError(f"Unable to load CSM config. Path:{csm_conf_path}")

        @staticmethod
        def load():
            csm_conf_target_path = os.path.join(const.CSM_CONF_PATH, const.CSM_CONF_FILE_NAME)
            if not os.path.exists(csm_conf_target_path):
                raise CsmSetupError("%s file is missing for csm setup" %const.CSM_CONF_FILE_NAME)
            Conf.load(const.CSM_GLOBAL_INDEX, Yaml(csm_conf_target_path))
            """
            Loading databse config
            """
            Setup.Config.load_db()

        @staticmethod
        def load_db():
            db_conf_target_path = os.path.join(const.CSM_CONF_PATH, const.DB_CONF_FILE_NAME)
            if not os.path.exists(db_conf_target_path):
                raise CsmSetupError("%s file is missing for csm setup" %const.DB_CONF_FILE_NAME)
            Conf.load(const.DATABASE_INDEX, Yaml(db_conf_target_path))

        @staticmethod
        def delete():
            Setup._run_cmd("rm -rf " + const.CSM_CONF_PATH)

        @staticmethod
        def reset():
            os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
            Setup._run_cmd("cp -rf " +const.CSM_SOURCE_CONF_PATH+ " " +const.ETC_PATH)

    def _config_cluster(self, args):
        """
        Instantiation of csm cluster with resources
        Create csm user
        """
        self._csm_resources = Conf.get(const.CSM_GLOBAL_INDEX, "HA.resources")
        self._csm_ra = {
            "csm_resource_agent": CsmResourceAgent(self._csm_resources)
        }
        self._ha_framework = PcsHAFramework(self._csm_ra)
        self._cluster = Cluster(const.INVENTORY_FILE, self._ha_framework)
        self._cluster.init(args['f'])
        CsmApi.set_cluster(self._cluster)

    def _cleanup_job(self, reset=False):
        """
        Check if csm_cleanup present is csm
            : If csm_cleanup present then configure cronjob
            : If csm_cleanup not present then through error
        """
        _proc = SimpleProcess("crontab -u " +self._user+ " -l")
        _output, _err, _rc = _proc.run(universal_newlines=True)
        if not reset:
            if "no crontab" not in _err:
                for job in _output.split('\n'):
                    if const.CSM_CRON_JOB in job:
                        return
            with open("/tmp/csm.cron", "w") as fi:
                if "no crontab" not in _err:
                    fi.write(_output)
                fi.write("0 1 * * *    {}\n".format(const.CSM_CRON_JOB))
            _output = Setup._run_cmd("crontab -u " +self._user+ " /tmp/csm.cron")
            os.remove("/tmp/csm.cron")
        else:
            if self._is_user_exist():
                if "no crontab" not in _err:
                    Setup._run_cmd("crontab -u " +self._user+ " -r")

    def _log_cleanup(self):
        """
        Delete all logs
        """
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path")
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

    def _rsyslog(self):
        """
        Configure rsyslog
        """
        if os.path.exists(const.RSYSLOG_DIR):
            Setup._run_cmd("cp -f " +const.SOURCE_RSYSLOG_PATH+ " " +const.RSYSLOG_PATH)
            Setup._run_cmd("cp -f " +const.SOURCE_SUPPORT_BUNDLE_CONF+ " " +const.SUPPORT_BUNDLE_CONF)
            Setup._run_cmd("systemctl restart rsyslog")
        else:
            raise CsmSetupError("rsyslog failed. %s directory missing." %const.RSYSLOG_DIR)

    def _rsyslog_common(self):
        """
        Configure common rsyslog and logrotate
        """
        if os.path.exists(const.LOGROTATE_DIR):
            Setup._run_cmd("cp -f " +const.CLEANUP_LOGROTATE_PATH+ " " +const.LOGROTATE_PATH)
        else:
            raise CsmSetupError("logrotate failed. %s dir missing." %const.LOGROTATE_DIR)
        if os.path.exists(const.CRON_DIR):
            Setup._run_cmd("cp -f " +const.SOURCE_CRON_PATH+ " " +const.DEST_CRON_PATH)
        else:
            raise CsmSetupError("cron failed. %s dir missing." %const.CRON_DIR)

    def _logrotate(self):
        """
        Configure logrotate
        """
        if os.path.exists(const.LOGROTATE_DIR):
            Setup._run_cmd("cp -f " +const.SOURCE_LOGROTATE_PATH+ " " +const.LOGROTATE_PATH)
            Setup._run_cmd("cp -f " +const.CLEANUP_LOGROTATE_PATH+ " " +const.LOGROTATE_PATH)
            Setup._run_cmd("chmod 644 " + const.LOGROTATE_PATH + "csm_agent_log.conf")
            Setup._run_cmd("chmod 644 " + const.LOGROTATE_PATH + "cleanup_log.conf")
        else:
            raise CsmSetupError("logrotate failed. %s dir missing." %const.LOGROTATE_DIR)

    def _set_rmq_node_id(self):
        """
        This method gets the nodes id from provisioner cli and updates
        in the config.
        """
        # Get get node id from provisioner cli and set to config
        node_id_data = Setup.get_data_from_provisioner_cli(const.GET_NODE_ID)
        if node_id_data:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}.{const.NODE1}", 
                            f"{const.NODE}{node_id_data[const.MINION_NODE1_ID]}")
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.CHANNEL}.{const.NODE2}", 
                            f"{const.NODE}{node_id_data[const.MINION_NODE2_ID]}")
            Conf.save(const.CSM_GLOBAL_INDEX)
        else:
            raise CsmSetupError(f"Unable to fetch system node ids info.")

    def _set_rmq_cluster_nodes(self):
        """
        This method gets the nodes names of the the rabbitmq cluster and writes
        in the config.
        """
        nodes = []
        nodes_found = False
        try:
            for count in range(0, const.RMQ_CLUSTER_STATUS_RETRY_COUNT):
                cmd_output = Setup._run_cmd(const.RMQ_CLUSTER_STATUS_CMD)
                for line in cmd_output[0].split('\n'):
                    if const.RUNNING_NODES in line:
                        nodes = re.findall(r"rabbit@([-\w]+)", line)
                        nodes_found = True
                if nodes_found:
                    break
                time.sleep(2**count)
            if nodes:
                conf_key = f"{const.CHANNEL}.{const.RMQ_HOSTS}"
                Conf.set(const.CSM_GLOBAL_INDEX, conf_key, nodes)
                Conf.save(const.CSM_GLOBAL_INDEX)
            else:
                raise CsmSetupError(f"Unable to fetch RMQ cluster nodes info.")
        except Exception as e:
            
            raise CsmSetupError(f"Setting RMQ cluster nodes failed. {e} - {str(traceback.print_exc())}")

    def _set_consul_vip(self):
        """
        This method gets the consul VIP for the current node and sets the
        value in database.yaml config.
        Seting the default values in case of command failure.
        """
        minion_id = None
        consul_host = None
        try:
            minion_id = Setup.get_salt_data_with_exception(const.GRAINS_GET, const.ID)
            if not minion_id:
                Log.logger.warn(f"Unable to fetch minion id for the node." \
                    f"Using {const.MINION_NODE1_ID}.")
                minion_id = const.MINION_NODE1_ID
            consul_vip_cmd = f"{const.CLUSTER}:{minion_id}:{const.NETWROK}:"\
                f"{const.DATA_NW}:{const.ROAMING_IP}"
            consul_host = Setup.get_salt_data_with_exception(const.PILLAR_GET, \
                consul_vip_cmd)
            if consul_host:
                Conf.set(const.DATABASE_INDEX, const.CONSUL_HOST_KEY, consul_host)
                Conf.save(const.DATABASE_INDEX)
        except Exception as e:
            raise CsmSetupError(f"Setting consul host with VIP failed. {e}")

    @classmethod
    def _get_faulty_node_uuid(self):
        """
        This method will get the faulty node uuid from provisioner.
        This uuid will be used to resolve the faulty alerts for replaced node.
        """
        faulty_minion_id = ''
        faulty_node_uuid = ''
        try:
            faulty_minion_id_cmd = "cluster:replace_node:minion_id"
            faulty_minion_id = Setup.get_salt_data_with_exception(const.PILLAR_GET, \
                faulty_minion_id_cmd)
            if not faulty_minion_id:
                Log.logger.warn("Fetching faulty node minion id failed.")
                raise CsmSetupError("Fetching faulty node minion failed.")
            faulty_node_uuid = Setup.get_salt_data_faulty_node_uuid\
                (faulty_minion_id, const.GRAINS_GET, 'node_id')
            if not faulty_node_uuid:
                Log.logger.warn("Fetching faulty node uuid failed.")
                raise CsmSetupError("Fetching faulty node uuid failed.")
            return faulty_node_uuid
        except Exception as e:
            Log.logger.warn(f"Fetching faulty node uuid failed. {e}")
            raise CsmSetupError(f"Fetching faulty node uuid failed. {e}")


    def _resolve_faulty_node_alerts(self, node_id):
        """
        This method resolves all the alerts for a fault replaced node.
        """
        try:
            conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
            db = DataBaseProvider(conf)
            alerts = []
            if db:
                loop = asyncio.get_event_loop()
                alerts_repository = AlertRepository(db)
                alerts = loop.run_until_complete\
                    (alerts_repository.retrieve_unresolved_by_node_id(node_id))
                if alerts:
                    for alert in alerts:
                        if not const.ENCLOSURE in alert.module_name:
                            alert.acknowledged = AlertModel.acknowledged.to_native(True)
                            alert.resolved = AlertModel.resolved.to_native(True)
                            loop.run_until_complete(alerts_repository.update(alert))
                else:
                    Log.logger.warn(f"No alerts found for node id: {node_id}")
            else:
                raise CsmSetupError("csm_setup refresh_config failed. Unbale to load db.")
        except Exception as ex:
            raise CsmSetupError(f"Refresh Context: Resolving of alerts failed. {ex}")

    def _configure_system_auto_restart(self):
        """
        Check's System Installation Type an dUpdate the Service File
        Accordingly.
        :return: None
        """
        is_auto_restart_required = list()
        if self._setup_info:
            for each_key in self._setup_info:
                comparison_data = const.EDGE_INSTALL_TYPE.get(each_key, None)
                #Check Key Exists:
                if comparison_data is None:
                    Log.logger.warn(f"Edge Installation missing key {each_key}")
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
            Log.logger.warn("Setup info does not exist.")
            is_auto_restart_required.append(True)
        if any(is_auto_restart_required):
            Log.logger.debug("Updating All setup file for Auto Restart on "
                             "Failure")
            Setup._update_service_file("#< RESTART_OPTION >",
                                      "RESTART=on-failure")
            Setup._run_cmd("systemctl daemon-reload")

    @staticmethod
    def _update_service_file(key, value):
        """
        Update CSM Agent and CSM Web service Files Depending on Job Type of
        Setup.
        """
        for each_service_file in const.CSM_SERVICE_FILES:
            service_file_data = Text(each_service_file).load()
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
        if "Product" in args.keys() and args["Product"] != "cortx":
            raise Exception("Not implemented for Product %s" %args["Product"])
        if "Component" in args.keys() and args["Component"] != "all":
            raise Exception("Not implemented for Component %s" %args["Component"])
        if "f" in args.keys() and args["f"] is True:
            raise Exception("Not implemented for force action")

    def post_install(self, args):
        """
        Perform post-install for csm
            : Configure csm user
            : Add Permission for csm user
            : Add cronjob for csm cleanup
        Post install is used after just all rpms are install but
        no service are started
        """
        try:
            self._verify_args(args)
            self._config_user()
            self._cleanup_job()
            self._configure_system_auto_restart()
        except Exception as e:
            raise CsmSetupError(f"csm_setup post_install failed. Error: {e} - {str(traceback.print_exc())}")

    def config(self, args):
        """
        Perform configuration for csm
            : Move conf file to etc
        Config is used to move update conf files one time configuration
        """
        try:
            self._verify_args(args)
            if not self._replacement_node_flag:
                self.Config.create(args)
        except Exception as e:
            raise CsmSetupError(f"csm_setup config failed. Error: {e} - {str(traceback.print_exc())}")

    def init(self, args):
        """
        Check and move required configuration file
        Init is used after all dependency service started
        """
        try:
            self._verify_args(args)
            self.Config.load()
            self._config_user_permission()
            if not self._replacement_node_flag:
                self._set_rmq_cluster_nodes()
                #TODO: Adding this implementation in try..except block to avoid build failure
                # This workaround will be fixed once JIRA ticket #10551 is resolved
                try:
                    self._set_rmq_node_id()
                except Exception as e:
                    Log.error(f"Failed to fetch system node ids info from provisioner cli.- {e}")
                self._set_consul_vip()
            self.ConfigServer.reload()
            self._rsyslog()
            self._logrotate()
            self._rsyslog_common()
            ha_check = Conf.get(const.CSM_GLOBAL_INDEX, "HA.enabled")
            if ha_check:
                self._config_cluster(args)
        except Exception as e:
            raise CsmSetupError(f"csm_setup init failed. Error: {e} - {str(traceback.print_exc())}")

    def reset(self, args):
        """
        Reset csm configuraion
        Soft: Soft Reset is used to restrat service with log cleanup
            - Cleanup all log
            - Reset conf
            - Restart service
        Hard: Hard reset is used to remove all configuration used by csm
            - Stop service
            - Cleanup all log
            - Delete all Dir created by csm
            - Cleanup Job
            - Disable csm service
            - Delete csm user
        """
        try:
            self._verify_args(args)
            if args["hard"]:
                self.Config.load()
                self.ConfigServer.stop()
                self._log_cleanup()
                self._config_user_permission(reset=True)
                self._cleanup_job(reset=True)
                self.Config.delete()
                self._config_user(reset=True)
            else:
                self.Config.reset()
                self.ConfigServer.restart()
        except Exception as e:
            raise CsmSetupError("csm_setup reset failed. Error: %s" %e)

    def refresh_config(self, args):
        """
        Refresh context for CSM
        """
        try:
            node_id = self._get_faulty_node_uuid()
            self._resolve_faulty_node_alerts(node_id)
            Log.logger.info(f"Resolved and acknowledged all the faulty node : {node_id} alerts")
        except Exception as e:
            raise CsmSetupError("csm_setup refresh_config failed. Error: %s" %e)
