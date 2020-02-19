#!/usr/bin/env python3

import sys
import os
import traceback
import json
from aiohttp import web
from importlib import import_module
import pathlib
from csm.common.runtime import Options


# TODO: Implement proper plugin factory design
def import_plugin_module(name):
    """ Import product-specific plugin module by the plugin name """

    product = Conf.get(const.CSM_GLOBAL_INDEX, "PRODUCT.name") or 'eos'
    return import_module(f'csm.{product}.plugins.{name}')


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
        from csm.core.data.db.db_provider import (DataBaseProvider, GeneralConfig)
        conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
        db = DataBaseProvider(conf)
        #todo: Remove the below line it only dumps the data when server starts.
        # kept for debugging alerts_storage.add_data()
        s3_plugin = import_plugin_module('s3')
        usl_service = UslService(s3_plugin.S3Plugin(), db)

        # Alert configuration

        alerts_repository = AlertRepository(db)
        alerts_service = AlertsAppService(alerts_repository)
        CsmRestApi.init(alerts_service, usl_service)

        pm = import_plugin_module('alert')
        CsmAgent.alert_monitor = AlertMonitorService(alerts_repository,
                                              pm.AlertPlugin())

        email_queue = EmailSenderQueue()
        email_queue.start_worker_sync()

        http_notifications = AlertHttpNotifyService()
        CsmAgent.alert_monitor.add_listener(http_notifications.handle_alert)
        CsmRestApi._app["alerts_service"] = alerts_service
        
        # Network file manager registration
        CsmRestApi._app["file_service"] = NetworkFileManager()

        # Stats service creation
        time_series_provider = TimelionProvider(const.AGGREGATION_RULE)
        time_series_provider.init()
        CsmRestApi._app["stat_service"] = StatsAppService(time_series_provider)

        # User/Session management services
        roles = Json(const.ROLES_MANAGEMENT).load()
        CsmRestApi._app["roles_service"] = RolesManagementService(roles)
        auth_service = AuthService()
        CsmRestApi._app.user_manager = UserManager(db)
        CsmRestApi._app.session_manager = SessionManager()
        CsmRestApi._app.login_service = LoginService(auth_service,
                                                     CsmRestApi._app.user_manager,
                                                     CsmRestApi._app.session_manager,
                                                     CsmRestApi._app["roles_service"])

        user_service = CsmUserService(CsmRestApi._app.user_manager)
        CsmRestApi._app["csm_user_service"] = user_service

        #S3 Plugin creation
        s3 = import_plugin_module('s3').S3Plugin()
        CsmRestApi._app["s3_iam_users_service"] = IamUsersService(s3)
        CsmRestApi._app["s3_account_service"] = S3AccountService(s3)
        CsmRestApi._app['s3_bucket_service'] = S3BucketService(s3)
        CsmRestApi._app["storage_capacity_service"] = StorageCapacityService()

        #TODO : This is a temporary fix for build failure.
        # We need to figure out a better solution.
        #global base_path
        # System config storage service
        system_config_mgr = SystemConfigManager(db)
        CsmRestApi._app["system_config_service"] = SystemConfigAppService(system_config_mgr,
            Template.from_file(const.CSM_SMTP_TEST_EMAIL_TEMPLATE_REL))

        email_notifier = AlertEmailNotifier(email_queue, system_config_mgr,
            Template.from_file(const.CSM_ALERT_EMAIL_NOTIFICATION_TEMPLATE_REL))
        CsmAgent.alert_monitor.add_listener(email_notifier.handle_alert)

        CsmRestApi._app["onboarding_config_service"] = OnboardingConfigService(db)

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
        CsmAgent.alert_monitor.start()
        CsmRestApi.run(port, https_conf, debug_conf)
        CsmAgent.alert_monitor.stop()


if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..', '..'))
    Options.parse(sys.argv)
    from csm.common.log import Log
    try:
        from csm.common.conf import Conf, ConfSection, DebugConf
        from csm.common.payload import Yaml
        from csm.common.payload import Payload, Json, JsonMessage, Dict
        from csm.common.template import Template
        from csm.core.blogic import const
        from csm.core.services.alerts import AlertsAppService, AlertEmailNotifier, \
                                            AlertMonitorService, AlertRepository
        from csm.core.services.stats import StatsAppService
        from csm.core.services.s3.iam_users import IamUsersService
        from csm.core.services.s3.accounts import S3AccountService
        from csm.core.services.s3.buckets import S3BucketService
        from csm.core.services.usl import UslService
        from csm.core.services.users import CsmUserService, UserManager
        from csm.core.services.sessions import SessionManager, LoginService, AuthService
        from csm.core.email.email_queue import EmailSenderQueue
        from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
        from csm.core.services.onboarding import OnboardingConfigService
        from csm.core.agent.api import CsmRestApi, AlertHttpNotifyService

        from csm.common.timeseries import TimelionProvider
        from csm.core.data.db.elasticsearch_db.storage import ElasticSearchDB
        from csm.core.services.storage_capacity import StorageCapacityService
        from csm.core.services.system_config import SystemConfigAppService, SystemConfigManager
        from csm.core.services.roles_management import RolesManagementService
        from csm.core.services.file import NetworkFileManager

        CsmAgent.init()
        CsmAgent.run()
    except Exception as e:
        Log.error(traceback.format_exc())
        if Options.debug:
            raise e
        os._exit(1)
