#!/usr/bin/env python3

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
from importlib import import_module
import pathlib


# TODO: Implement proper plugin factory design
def import_plugin_module(name):
    """Import product-specific plugin module by the plugin name."""
    return import_module(f'csm.plugins.{const.PLUGIN_DIR}.{name}')


class CsmAgent:
    """CSM Core Agent / Deamon."""

    @staticmethod
    def init():
        """Initializa CSM agent."""
        CsmAgent.load_csm_config_indices()
        Conf.load(const.DB_DICT_INDEX, 'dict:{"k":"v"}')
        Conf.load(const.CSM_DICT_INDEX, 'dict:{"k":"v"}')
        Conf.copy(const.CSM_GLOBAL_INDEX, const.CSM_DICT_INDEX)
        Conf.copy(const.DATABASE_INDEX, const.DB_DICT_INDEX)
        backup_count = Conf.get(const.CSM_GLOBAL_INDEX, "Log>total_files")
        file_size_in_mb = Conf.get(const.CSM_GLOBAL_INDEX, "Log>file_size")
        log_level = "DEBUG" if Options.debug else Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_level")
        console_output = Conf.get(const.CSM_GLOBAL_INDEX, "Log>console_logging") == "true"
        Log.init("csm_agent",
                 backup_count=int(backup_count) if backup_count else None,
                 file_size_in_mb=int(file_size_in_mb) if file_size_in_mb else None,
                 log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path"),
                 level=log_level, console_output=console_output)

        from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
        db_config = {
            'databases': Conf.get(const.DB_DICT_INDEX, 'databases'),
            'models': Conf.get(const.DB_DICT_INDEX, 'models')
        }
        db_config['databases']["es_db"]["config"][const.PORT] = int(
            db_config['databases']["es_db"]["config"][const.PORT])
        db_config['databases']["es_db"]["config"]["replication"] = int(
            db_config['databases']["es_db"]["config"]["replication"])
        db_config['databases']["consul_db"]["config"][const.PORT] = int(
            db_config['databases']["consul_db"]["config"][const.PORT])
        conf = GeneralConfig(db_config)
        db = DataBaseProvider(conf)

        # Remove all Old Shutdown Cron Jobs
        CronJob(Conf.get(const.CSM_GLOBAL_INDEX, const.NON_ROOT_USER_KEY)).remove_job(
            const.SHUTDOWN_COMMENT)
        # TODO: Remove the below line it only dumps the data when server starts.
        # kept for debugging alerts_storage.add_data()

        # Clearing cached files
        cached_files = glob.glob(const.CSM_TMP_FILE_CACHE_DIR + '/*')
        for f in cached_files:
            os.remove(f)

        # CSM REST API initialization
        CsmRestApi.init()

        # system status
        system_status_service = SystemStatusService()
        CsmRestApi._app[const.SYSTEM_STATUS_SERVICE] = system_status_service

        # Heath configuration
        health_plugin = import_plugin_module(const.HEALTH_PLUGIN)
        health_plugin_obj = health_plugin.HealthPlugin(CortxHAFramework())
        health_service = HealthAppService(health_plugin_obj)
        CsmRestApi._app[const.HEALTH_SERVICE] = health_service
        message_bus_obj = MessageBusComm(Conf.get(const.CONSUMER_INDEX, const.KAFKA_ENDPOINTS),
                                         unblock_consumer=True)

        CsmAgent._configure_cluster_management_service(message_bus_obj)

        # Stats service creation
        time_series_provider = TimelionProvider(const.AGGREGATION_RULE)
        time_series_provider.init()
        kafka_endpoints = Conf.get(const.CONSUMER_INDEX, const.KAFKA_ENDPOINTS)
        CsmRestApi._app["stat_service"] = StatsAppService(
            time_series_provider, MessageBusComm(kafka_endpoints, unblock_consumer=True))
        # User/Role/Session management services
        roles = Json(const.ROLES_MANAGEMENT).load()
        auth_service = AuthService()
        user_manager = UserManager(db)
        role_manager = RoleManager(roles)
        session_manager = SessionManager(db)
        CsmRestApi._app.login_service = LoginService(auth_service,
                                                     user_manager,
                                                     role_manager,
                                                     session_manager)

        roles_service = RoleManagementService(role_manager)
        CsmRestApi._app["roles_service"] = roles_service
        # RGW S3 service
        CsmAgent._configure_s3_services()

        user_service = CsmUserService(user_manager)
        CsmRestApi._app[const.CSM_USER_SERVICE] = user_service
        CsmRestApi._app[const.STORAGE_CAPACITY_SERVICE] = StorageCapacityService()
        CsmRestApi._app[const.UNSUPPORTED_FEATURES_SERVICE] = UnsupportedFeaturesService()
        CsmRestApi._app[const.VERSION_VALIDATION_SERVICE] = VersionValidationService()

    @staticmethod
    def _configure_cluster_management_service(message_bus_obj):
        # Cluster Management configuration
        cluster_management_plugin = import_plugin_module(const.CLUSTER_MANAGEMENT_PLUGIN)
        cluster_management_plugin_obj = cluster_management_plugin.ClusterManagementPlugin(
            CortxHAFramework())
        cluster_management_service = ClusterManagementAppService(
            cluster_management_plugin_obj, message_bus_obj)
        CsmRestApi._app[const.CLUSTER_MANAGEMENT_SERVICE] = cluster_management_service

    @staticmethod
    def _configure_s3_services():
        s3_plugin = import_plugin_module(const.RGW_PLUGIN)
        s3_plugin_obj = s3_plugin.RGWPlugin()
        CsmRestApi._app[const.S3_IAM_USERS_SERVICE] = S3IAMUserService(s3_plugin_obj)
        CsmRestApi._app[const.S3_BUCKET_SERVICE] = BucketService(s3_plugin_obj)

    @staticmethod
    def _get_consul_config():
        protocol, host, port, secret, each_endpoint = '','','','',''
        endpoint_list = Conf.get(const.CONSUMER_INDEX, const.CONSUL_ENDPOINTS_KEY)
        secret = Conf.get(const.CONSUMER_INDEX, const.CONSUL_SECRET_KEY)
        for each_endpoint in endpoint_list:
            if 'http' in each_endpoint:
                protocol, host, port = ServiceUrls.parse_url(each_endpoint)
                break
        return protocol, host, port, secret, each_endpoint

    @staticmethod
    def load_csm_config_indices():
        """Load CSM configuration from the database."""
        set_config_flag = False
        Conf.load(const.CONSUMER_INDEX, Options.config)
        _, consul_host, consul_port, _, _ = CsmAgent._get_consul_config()
        if consul_host and consul_port:
            try:
                ConsulV().validate_service_status(consul_host, consul_port)
                Conf.load(const.CSM_GLOBAL_INDEX,
                          f"consul://{consul_host}:{consul_port}/{const.CSM_CONF_BASE}")
                Conf.load(const.DATABASE_INDEX,
                          f"consul://{consul_host}:{consul_port}/{const.DATABASE_CONF_BASE}")
                set_config_flag = True
            except VError as ve:
                Log.error(f"Unable to fetch the configurations from consul: {ve}")
                raise CsmInternalError(desc="Unable to fetch the configurations")

        if not set_config_flag:
            conf_path = Conf.get(const.CONSUMER_INDEX, const.CONFIG_STORAGE_DIR_KEY)
            csm_config_dir = os.path.join(conf_path, const.NON_ROOT_USER)
            Conf.load(const.CSM_GLOBAL_INDEX,
                      f"yaml://{csm_config_dir}/{const.CSM_CONF_FILE_NAME}")
            Conf.load(const.DATABASE_INDEX,
                      f"yaml://{csm_config_dir}/{const.DB_CONF_FILE_NAME}")
            set_config_flag = True

    @staticmethod
    def _daemonize():
        """Change process into background service."""
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
        """Run CSM agent."""
        https_conf = ConfSection(Conf.get(const.CSM_DICT_INDEX, "HTTPS"))
        debug_conf = DebugConf(ConfSection(Conf.get(const.CSM_DICT_INDEX, "DEBUG")))
        port = Conf.get(const.CSM_GLOBAL_INDEX, const.AGENT_PORT)

        if Options.daemonize:
            CsmAgent._daemonize()
        CsmRestApi.run(port, https_conf, debug_conf)
        Log.info("Stopping Message Bus client")
        CsmRestApi._app["stat_service"].stop_msg_bus()
        Log.info("Finished stopping csm agent")


if __name__ == '__main__':
    sys.path.append(os.path.join(
        os.path.dirname(pathlib.Path(__file__)), '..', '..', '..'))
    sys.path.append(os.path.join(
        os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..'))
    sys.path.append(os.path.join(
        os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..', '..'))
    from cortx.utils.log import Log
    from csm.common.runtime import Options
    Options.parse(sys.argv)
    from csm.common.conf import ConfSection, DebugConf
    from cortx.utils.conf_store.conf_store import Conf
    from csm.common.payload import Json
    from csm.core.blogic import const
    from csm.core.services.health import HealthAppService
    from csm.core.services.cluster_management import ClusterManagementAppService
    from csm.core.services.stats import StatsAppService
    from csm.core.services.users import CsmUserService, UserManager
    from csm.core.services.roles import RoleManagementService, RoleManager
    from csm.core.services.sessions import SessionManager, LoginService, AuthService
    from csm.core.agent.api import CsmRestApi
    from csm.common.timeseries import TimelionProvider
    from csm.common.ha_framework import CortxHAFramework
    from cortx.utils.cron import CronJob
    from cortx.utils.validator.v_consul import ConsulV
    from cortx.utils.validator.error import VError
    from csm.core.services.storage_capacity import StorageCapacityService
    from csm.common.errors import CsmInternalError
    from csm.core.services.unsupported_features import UnsupportedFeaturesService
    from csm.core.services.system_status import SystemStatusService
    from csm.common.comm import MessageBusComm
    from csm.core.services.rgw.s3.users import S3IAMUserService
    from csm.core.services.rgw.s3.bucket import BucketService
    from csm.core.services.version import VersionValidationService
    from csm.common.service_urls import ServiceUrls

    try:
        client = None
        CsmAgent.init()
        CsmAgent.run()
    except Exception as e:
        Log.error(traceback.format_exc())
        if Options.debug:
            raise e
        os._exit(1)
