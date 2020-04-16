#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          setup.py
 Description:       Setup of csm and their component

 Creation Date:     23/08/2019
 Author:            Ajay Paratmandali

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import sys
import crypt
import pwd
from csm.common.conf import Conf
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from csm.common.errors import CsmSetupError
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.common.ha_framework import PcsHAFramework
from csm.common.cluster import Cluster
from csm.core.agent.api import CsmApi

# try:
#     from salt import client
# except ModuleNotFoundError:
client = None


class Setup:
    def __init__(self):
        self._user = const.NON_ROOT_USER
        self._password = crypt.crypt(const.NON_ROOT_USER_PASS, "22")
        self._uid = self._gid = -1

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

    def _config_user(self, reset=False):
        """
        Check user already exist and create if not exist
        If reset true then delete user
        """
        if not reset:
            if not self._is_user_exist():
                Setup._run_cmd("useradd -M -p "+self._password+" "+ self._user)
                if not self._is_user_exist():
                    raise CsmSetupError("Unable to create %s user" % self._user)
        else:
            if self._is_user_exist():
                Setup._run_cmd("userdel -r " +self._user)

    def _config_user_permission_set(self, bundle_path, crt, key):
        """
        Set User Permission
        """
        os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
        os.makedirs(const.CSM_PIDFILE_PATH, exist_ok=True)
        os.makedirs(const.CSM_LOG_PATH, exist_ok=True)
        os.makedirs(bundle_path, exist_ok=True)
        os.makedirs(const.CSM_TMP_FILE_CACHE_DIR, exist_ok=True)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_PATH)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_TMP_FILE_CACHE_DIR)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + bundle_path)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_LOG_PATH)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_CONF_PATH)
        Setup._run_cmd("setfacl -R -m u:" + self._user + ":rwx " + const.CSM_PIDFILE_PATH)
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
        def create():
            """
            This Function Creates the CSM Conf File on Required Location.
            :return:
            """
            Setup._run_cmd(f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")
            if not client:
                return None
            csm_conf_path = os.path.join(const.CSM_CONF_PATH, const.CSM_CONF_FILE_NAME)
            # read username's and password's for S3 and RMQ
            open_ldap_credentials = client.Caller().function(const.PILLAR_GET,
                                                             const.OPEN_LDAP)
            sspl_config = client.Caller().function(const.PILLAR_GET, const.SSPL)
            # Read Current CSM Config FIle.
            conf_file_data = Yaml(csm_conf_path).load()
            # Edit Current Config File.
            conf_file_data[const.CHANNEL][const.USERNAME] = sspl_config.get(
                const.RMQ, {}).get(const.USER)
            conf_file_data[const.CHANNEL][const.PASSWORD] = sspl_config.get(
                const.RMQ, {}).get(const.SECRET)
            conf_file_data[const.S3][const.LDAP_LOGIN] = open_ldap_credentials.get(
                const.IAM_ADMIN, {}).get(const.USER)
            conf_file_data[const.S3][const.LDAP_PASSWORD] = open_ldap_credentials.get(
                const.IAM_ADMIN, {}).get(const.SECRET)
            # Update the Current Config File.
            Yaml(csm_conf_path).dump(conf_file_data)

        @staticmethod
        def load():
            if not os.path.exists(const.CSM_SOURCE_CONF):
                raise CsmSetupError("%s file is missing for csm setup" %const.CSM_SOURCE_CONF)
            Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_SOURCE_CONF))

        @staticmethod
        def delete():
            Setup._run_cmd("rm -rf " + const.CSM_CONF_PATH)

        @staticmethod
        def reset():
            os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
            Setup._run_cmd("cp -rf " +const.CSM_SOURCE_CONF_PATH+ " " +const.ETC_PATH)

    def _config_cluster(self):
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
        self._cluster.init()
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
        Setup._run_cmd("rm -rf " +const.CSM_LOG_PATH)

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


# TODO: Devide changes in backend and frontend
# TODO: Optimise use of args for like product, force, component
class CsmSetup(Setup):
    def __init__(self):
        super(CsmSetup, self).__init__()
        pass

    def _verify_args(self, args):
        """
        Verify args for actions
        """
        if "Product" in args.keys() and args["Product"] != "ees":
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
        except Exception as e:
            raise CsmSetupError("csm_setup post_install failed. Error: %s" %e)

    def config(self, args):
        """
        Perform configuration for csm
            : Move conf file to etc
        Config is used to move update conf files one time configuration
        """
        try:
            self._verify_args(args)

            self.Config.create()
        except Exception as e:
            raise CsmSetupError("csm_setup config failed. Error: %s" %e)

    def init(self, args):
        """
        Check and move required configuration file
        Init is used after all dependency service started
        """
        try:
            self._verify_args(args)
            self.Config.load()
            self._config_user_permission()
            self.ConfigServer.reload()
            self._rsyslog()
            self._logrotate()
            self._rsyslog_common()
            ha_check = Conf.get(const.CSM_GLOBAL_INDEX, "HA.enabled")
            if ha_check:
                self._config_cluster()
        except Exception as e:
            raise CsmSetupError("csm_setup init failed. Error: %s" %e)

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
