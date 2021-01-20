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

    return import_module(f'csm.plugins.{const.PLUGIN_DIR}.{name}')


class CsmAgent:
    """ CSM Core Agent / Deamon """

    @staticmethod
    def init():
        Conf.load(const.CSM_GLOBAL_INDEX, f"yaml://{const.CSM_CONF}")
        syslog_port = Conf.get(const.CSM_GLOBAL_INDEX, "Log>syslog_port")
        backup_count = Conf.get(const.CSM_GLOBAL_INDEX, "Log>total_files")
        file_size_in_mb = Conf.get(const.CSM_GLOBAL_INDEX, "Log>file_size")
        Log.init("csm_agent",
               syslog_server=Conf.get(const.CSM_GLOBAL_INDEX, "Log>syslog_server"),
               syslog_port= int(syslog_port) if syslog_port else syslog_port,
               backup_count= int(backup_count) if backup_count else backup_count,
               file_size_in_mb=int(file_size_in_mb) if file_size_in_mb else file_size_in_mb,
               log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path"),
               level=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_level"))
        if Conf.get(const.CSM_GLOBAL_INDEX, "DEPLOYMENT>mode") != const.DEV:
            Conf.decrypt_conf()
        from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
        db_config = Yaml(const.DATABASE_CONF).load()
        db_config['databases']["es_db"]["config"][const.PORT] = int(
            db_config['databases']["es_db"]["config"][const.PORT])
        db_config['databases']["es_db"]["config"]["replication"] = int(
            db_config['databases']["es_db"]["config"]["replication"])
        db_config['databases']["consul_db"]["config"][const.PORT] = int(
            db_config['databases']["consul_db"]["config"][const.PORT])
        conf = GeneralConfig(db_config)
        db = DataBaseProvider(conf)

        Conf.load(const.DATABASE_INDEX, f"yaml://{const.DATABASE_CONF}")

        #Remove all Old Shutdown Cron Jobs
        CronJob(const.NON_ROOT_USER).remove_job(const.SHUTDOWN_COMMENT)
        #todo: Remove the below line it only dumps the data when server starts.
        # kept for debugging alerts_storage.add_data()

        # Clearing cached files
        cached_files = glob.glob(const.CSM_TMP_FILE_CACHE_DIR + '/*')
        for f in cached_files:
            os.remove(f)

        # Alert configuration
        alerts_repository = AlertRepository(db)
        alerts_service = AlertsAppService(alerts_repository)
        CsmRestApi.init(alerts_service)

        # settting usl polling
        usl_polling_log = Conf.get(const.CSM_GLOBAL_INDEX, "Log>usl_polling_log")
        CsmRestApi._app[const.USL_POLLING_LOG] = usl_polling_log

        # system status
        system_status_service = SystemStatusService()
        CsmRestApi._app[const.SYSTEM_STATUS_SERVICE] = system_status_service

        #Heath configuration
        health_repository = HealthRepository()
        health_plugin = import_plugin_module(const.HEALTH_PLUGIN)
        health_plugin_obj = health_plugin.HealthPlugin()
        health_service = HealthAppService(health_repository, alerts_repository, \
            health_plugin_obj)
        CsmAgent.health_monitor = HealthMonitorService(\
                health_plugin_obj, health_service)
        CsmRestApi._app[const.HEALTH_SERVICE] = health_service

        http_notifications = AlertHttpNotifyService()
        pm = import_plugin_module(const.ALERT_PLUGIN)
        CsmAgent.alert_monitor = AlertMonitorService(alerts_repository,\
                pm.AlertPlugin(), CsmAgent.health_monitor.health_plugin, \
                http_notifications)
        email_queue = EmailSenderQueue()
        email_queue.start_worker_sync()

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

        roles_service = RoleManagementService(role_manager)
        CsmRestApi._app["roles_service"] = roles_service


        #TODO : This is a temporary fix for build failure.
        # We need to figure out a better solution.
        #global base_path
        # System config storage service
        system_config_mgr = SystemConfigManager(db)

        email_notifier = AlertEmailNotifier(email_queue, system_config_mgr,
            Template.from_file(const.CSM_ALERT_EMAIL_NOTIFICATION_TEMPLATE_REL),
            user_manager)
        CsmAgent.alert_monitor.add_listener(email_notifier.handle_alert)

        CsmRestApi._app["onboarding_config_service"] = OnboardingConfigService(db)
        # audit log download api
        audit_mngr = AuditLogManager(db)
        CsmRestApi._app["audit_log"] = AuditService(audit_mngr)

        try:
            # TODO: consider a more safe storage
            params = {
                "username": const.NON_ROOT_USER,
                "password": Conf.get(const.CSM_GLOBAL_INDEX, "CSM.password")
            }
            provisioner = import_plugin_module(const.PROVISIONER_PLUGIN).ProvisionerPlugin(**params)
        except CsmError as ce:
            Log.error(f"Unable to load Provisioner plugin: {ce}")

        # S3 Plugin creation
        s3 = import_plugin_module(const.S3_PLUGIN).S3Plugin()
        CsmRestApi._app[const.S3_IAM_USERS_SERVICE] = IamUsersService(s3, provisioner)
        CsmRestApi._app[const.S3_ACCOUNT_SERVICE] = S3AccountService(s3, provisioner)
        CsmRestApi._app[const.S3_BUCKET_SERVICE] = S3BucketService(s3, provisioner)
        CsmRestApi._app[const.S3_ACCESS_KEYS_SERVICE] = S3AccessKeysService(s3)

        user_service = CsmUserService(provisioner, user_manager)
        CsmRestApi._app[const.CSM_USER_SERVICE] = user_service
        update_repo = UpdateStatusRepository(db)
        security_service = SecurityService(db, provisioner)
        CsmRestApi._app[const.HOTFIX_UPDATE_SERVICE] = HotfixApplicationService(
            Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE.hotfix_store_path'), provisioner, update_repo)
        CsmRestApi._app[const.FW_UPDATE_SERVICE] = FirmwareUpdateService(provisioner,
                Conf.get(const.CSM_GLOBAL_INDEX, 'UPDATE.firmware_store_path'), update_repo)
        CsmRestApi._app[const.SYSTEM_CONFIG_SERVICE] = SystemConfigAppService(db, provisioner,
            security_service, system_config_mgr, Template.from_file(const.CSM_SMTP_TEST_EMAIL_TEMPLATE_REL))
        CsmRestApi._app[const.STORAGE_CAPACITY_SERVICE] = StorageCapacityService(provisioner)

        CsmRestApi._app[const.SECURITY_SERVICE] = security_service
        CsmRestApi._app[const.PRODUCT_VERSION_SERVICE] = ProductVersionService(provisioner)

        CsmRestApi._app[const.APPLIANCE_INFO_SERVICE] = ApplianceInfoService()
        # USL Service
        CsmRestApi._app[const.USL_SERVICE] = UslService(s3, db, provisioner)

        # Plugin for Maintenance
        # TODO : Replace PcsHAFramework with hare utility
        CsmRestApi._app[const.MAINTENANCE_SERVICE] = MaintenanceAppService(CortxHAFramework(),  provisioner, db)

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
        Log.info("Started stopping csm agent")
        CsmAgent.alert_monitor.stop()
        Log.info("Finished stopping alert monitor service")
        CsmAgent.health_monitor.stop()
        Log.info("Finished stopping csm agent")


if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..', '..'))
    from cortx.utils.log import Log
    from csm.common.runtime import Options
    Options.parse(sys.argv)
    from cortx.utils.conf_store.conf_store import ConfSection, DebugConf
    from cortx.utils.conf_store.conf_store import Conf
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
    from csm.core.services.s3.access_keys import S3AccessKeysService
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
    from csm.common.ha_framework import CortxHAFramework, PcsHAFramework
    from cortx.utils.cron import CronJob
    from csm.core.services.maintenance import MaintenanceAppService
    from cortx.utils.data.db.elasticsearch_db.storage import ElasticSearchDB
    from csm.core.services.storage_capacity import StorageCapacityService
    from csm.core.services.system_config import SystemConfigAppService, SystemConfigManager
    from csm.core.services.audit_log import  AuditLogManager, AuditService
    from csm.core.services.file_transfer import DownloadFileManager
    from csm.core.services.firmware_update import FirmwareUpdateService
    from csm.common.errors import CsmError
    from cortx.utils.security.cipher import Cipher, CipherInvalidToken
    from csm.core.services.version import ProductVersionService
    from csm.core.services.appliance_info import ApplianceInfoService
    from csm.core.services.system_status import SystemStatusService
    try:
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
