#!/usr/bin/env python3

import sys
import os
import glob
import traceback
import json
from aiohttp import web
from importlib import import_module
import pathlib

# TODO: Implement proper plugin factory design
def import_plugin_module(name):
    """ Import product-specific plugin module by the plugin name """

    product = Conf.get(const.CSM_GLOBAL_INDEX, "PRODUCT.name") or 'eos'
    return import_module(f'csm.plugins.{product}.{name}')


class CsmAgent:
    """ CSM Core Agent / Deamon """

    @staticmethod
    def init():
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
        Log.init("csm_agent",
               syslog_server=Conf.get(const.CSM_GLOBAL_INDEX, "Log.syslog_server"),
               syslog_port=Conf.get(const.CSM_GLOBAL_INDEX, "Log.syslog_port"),
               backup_count=Conf.get(const.CSM_GLOBAL_INDEX, "Log.total_files"),
               file_size_in_mb=Conf.get(const.CSM_GLOBAL_INDEX, "Log.file_size"),
               log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path"),
               level=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_level"))
        CsmAgent.decrypt_conf()
        from eos.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
        conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
        db = DataBaseProvider(conf)

        try:
            # TODO: consider a more safe storage
            params = {
                "username": const.NON_ROOT_USER,
                "password": const.NON_ROOT_USER_PASS
            }
            provisioner = import_plugin_module(const.PROVISIONER_PLUGIN).ProvisionerPlugin(**params)
        except CsmError as ce:
            Log.error(f"Unable to load Provisioner plugin: {ce}")

        #todo: Remove the below line it only dumps the data when server starts.
        # kept for debugging alerts_storage.add_data()
        s3_plugin = import_plugin_module('s3')
        usl_service = UslService(s3_plugin.S3Plugin(), db, provisioner)

        # Clearing cached files
        cached_files = glob.glob(const.CSM_TMP_FILE_CACHE_DIR + '/*')
        for f in cached_files:
            os.remove(f)

        # Alert configuration
        alerts_repository = AlertRepository(db)
        alerts_service = AlertsAppService(alerts_repository)
        CsmRestApi.init(alerts_service, usl_service)

        #Heath configuration
        health_repository = HealthRepository()
        health_plugin = import_plugin_module(const.HEALTH_PLUGIN)
        health_plugin_obj = health_plugin.HealthPlugin()
        health_service = HealthAppService(health_repository, alerts_repository, \
            health_plugin_obj)
        CsmAgent.health_monitor = HealthMonitorService(\
                health_plugin_obj, health_service)
        CsmRestApi._app[const.HEALTH_SERVICE] = health_service

        pm = import_plugin_module(const.ALERT_PLUGIN)
        CsmAgent.alert_monitor = AlertMonitorService(alerts_repository,\
                pm.AlertPlugin(), CsmAgent.health_monitor.health_plugin)
        email_queue = EmailSenderQueue()
        email_queue.start_worker_sync()

        http_notifications = AlertHttpNotifyService()
        CsmAgent.alert_monitor.add_listener(http_notifications.handle_alert)
        CsmRestApi._app["alerts_service"] = alerts_service

       # Network file manager registration
        CsmRestApi._app["download_service"] = DownloadFileManager()

        # Stats service creation
        time_series_provider = TimelionProvider(const.AGGREGATION_RULE)
        time_series_provider.init()
        CsmRestApi._app["stat_service"] = StatsAppService(time_series_provider)

        # User/Role/Session management services
        roles = Json(const.ROLES_MANAGEMENT).load()
        auth_service = AuthService()
        user_manager = UserManager(db)
        role_manager = RoleManager(roles)
        session_manager = SessionManager()
        CsmRestApi._app.login_service = LoginService(auth_service,
                                                     user_manager,
                                                     role_manager,
                                                     session_manager)

        user_service = CsmUserService(user_manager)
        CsmRestApi._app["csm_user_service"] = user_service

        roles_service = RoleManagementService(role_manager)
        CsmRestApi._app["roles_service"] = roles_service


        #S3 Plugin creation
        s3 = import_plugin_module(const.S3_PLUGIN).S3Plugin()
        CsmRestApi._app["s3_iam_users_service"] = IamUsersService(s3)
        CsmRestApi._app["s3_account_service"] = S3AccountService(s3)
        CsmRestApi._app['s3_bucket_service'] = S3BucketService(s3)

        # Plugin for Maintenance
        #TODO : Replace PcsHAFramework with hare utility
        CsmRestApi._app["maintenance"] = MaintenanceAppService(PcsHAFramework())

        #TODO : This is a temporary fix for build failure.
        # We need to figure out a better solution.
        #global base_path
        # System config storage service
        system_config_mgr = SystemConfigManager(db)

        email_notifier = AlertEmailNotifier(email_queue, system_config_mgr,
            Template.from_file(const.CSM_ALERT_EMAIL_NOTIFICATION_TEMPLATE_REL))
        CsmAgent.alert_monitor.add_listener(email_notifier.handle_alert)

        CsmRestApi._app["onboarding_config_service"] = OnboardingConfigService(db)
        # audit log download api
        audit_mngr = AuditLogManager(db)
        CsmRestApi._app["audit_log"] = AuditService(audit_mngr)

        update_repo = UpdateStatusRepository(db)
        security_service = SecurityService(db, provisioner)
        CsmRestApi._app[const.HOTFIX_UPDATE_SERVICE] = HotfixApplicationService(
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE.hotfix_store_path'), provisioner, update_repo)
        CsmRestApi._app[const.FW_UPDATE_SERVICE] = FirmwareUpdateService(provisioner,
                Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE.firmware_store_path'), update_repo)
        CsmRestApi._app[const.SYSTEM_CONFIG_SERVICE] = SystemConfigAppService(provisioner,
            security_service, system_config_mgr, Template.from_file(const.CSM_SMTP_TEST_EMAIL_TEMPLATE_REL))
        CsmRestApi._app[const.STORAGE_CAPACITY_SERVICE] = StorageCapacityService(provisioner)

        CsmRestApi._app[const.SECURITY_SERVICE] = security_service

    @staticmethod
    def decrypt_conf():
        """
        THis Method Will Decrypt all the Passwords in Config and Will Load the Same in CSM.
        :return:
        """
        if not client:
            Log.warn("Salt Module Not Found.")
            return None
        cluster_id = client.Caller().function(const.GRAINS_GET, const.CLUSTER_ID)
        for each_key in const.DECRYPTION_KEYS:
            cipher_key = Cipher.generate_key(cluster_id,
                                             const.DECRYPTION_KEYS[each_key])
            encrypted_value = Conf.get(const.CSM_GLOBAL_INDEX, each_key)
            try:
                decrypted_value = Cipher.decrypt(cipher_key,
                                                 encrypted_value.encode("utf-8"))
                Conf.set(const.CSM_GLOBAL_INDEX, each_key,
                         decrypted_value.decode("utf-8"))
            except CipherInvalidToken as error:
                Log.warn(f"Decryption for {each_key} Failed. {error}")

    @staticmethod
    def _daemonize():
        """ Change process into background service """
        if not os.path.isdir("/var/run/csm/"):
            os.makedirs('/var/run/csm/')
        try:
            # Check and Create a PID file for systemd
            pidfile = "/var/run/csm/csm_agent.pid"
            pid = ""
            if os.path.isfile(pidfile):
                with open(pidfile) as f:
                    pid = f.readline().strip()
            if len(pid) and os.path.exists("/proc/%s" % pid):
                print("Another instance of CSM agent with pid %s is active. exiting..." % pid)
                sys.exit(0)

            pid = os.fork()
            if pid > 0:
                print("CSM agent started with pid %d" % pid)
                os._exit(0)

        except OSError as e:
            print("Unable to fork.\nerror(%d): %s" % (e.errno, e.strerror))
            os._exit(1)

        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))

    @staticmethod
    def run():
        https_conf = ConfSection(Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS"))
        debug_conf = DebugConf(ConfSection(Conf.get(const.CSM_GLOBAL_INDEX, "DEBUG")))
        port = Conf.get(const.CSM_GLOBAL_INDEX, 'CSM_SERVICE.CSM_AGENT.port')

        if not Options.debug:
            CsmAgent._daemonize()
        CsmAgent.health_monitor.start()
        CsmAgent.alert_monitor.start()
        CsmRestApi.run(port, https_conf, debug_conf)
        CsmAgent.health_monitor.stop()
        CsmAgent.alert_monitor.stop()


if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..', '..'))
    from eos.utils.log import Log
    from csm.common.runtime import Options
    Options.parse(sys.argv)
    try:
        from csm.common.conf import Conf, ConfSection, DebugConf
        from csm.common.payload import Yaml
        from csm.common.payload import Payload, Json, JsonMessage, Dict
        from csm.common.template import Template
        from csm.core.blogic import const
        from csm.core.services.alerts import AlertsAppService, AlertEmailNotifier, \
                                            AlertMonitorService, AlertRepository
        from csm.core.services.health import HealthAppService, HealthRepository \
                , HealthMonitorService
        from csm.core.services.stats import StatsAppService
        from csm.core.services.s3.iam_users import IamUsersService
        from csm.core.services.s3.accounts import S3AccountService
        from csm.core.services.s3.buckets import S3BucketService
        from csm.core.services.usl import UslService
        from csm.core.services.users import CsmUserService, UserManager
        from csm.core.services.roles import RoleManagementService, RoleManager
        from csm.core.services.sessions import SessionManager, LoginService, AuthService
        from csm.core.services.security import SecurityService
        from csm.core.services.hotfix_update import HotfixApplicationService
        from csm.core.repositories.update_status import UpdateStatusRepository
        from csm.core.email.email_queue import EmailSenderQueue
        from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
        from csm.core.services.onboarding import OnboardingConfigService
        from csm.core.agent.api import CsmRestApi, AlertHttpNotifyService

        from csm.common.timeseries import TimelionProvider
        from csm.common.ha_framework import PcsHAFramework
        from csm.core.services.maintenance import MaintenanceAppService
        from eos.utils.data.db.elasticsearch_db.storage import ElasticSearchDB
        from csm.core.services.storage_capacity import StorageCapacityService
        from csm.core.services.system_config import SystemConfigAppService, SystemConfigManager
        from csm.core.services.audit_log import  AuditLogManager, AuditService
        from csm.core.services.file_transfer import DownloadFileManager
        from csm.core.services.firmware_update import FirmwareUpdateService
        from csm.common.errors import CsmError
        from eos.utils.security.cipher import Cipher, CipherInvalidToken
        # try:
        #     from salt import client
        # except ModuleNotFoundError:
        client = None
        CsmAgent.init()
        CsmAgent.run()
    except Exception as e:
        Log.error(traceback.format_exc())
        if Options.debug:
            raise e
        os._exit(1)
