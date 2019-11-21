#!/usr/bin/env python3

import sys
import os
import traceback
import json
from aiohttp import web
from importlib import import_module

# Global options for debugging purposes
# It is quick and dirty temporary solution
class Opt:
    def __init__(self, argv):
        self.debug = len(argv) > 1 and argv[1] == '--debug'

global opt

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

        from csm.core.data.db.db_provider import (DataBaseProvider,
                GeneralConfig)        

        conf = GeneralConfig({
            "databases": {
                "es_db": {
                    "import_path": "ElasticSearchDB",
                    "config": {
                        "host": "localhost",
                        "port": 9200,
                        "login": "",
                        "password": ""
                    }
                }
            },
            "models": [
                {
                    "import_path": "csm.core.blogic.models.alerts.AlertModel",
                    "database": "es_db",
                    "config": {
                        "es_db":
                        {
                            "collection": "alerts"
                        }
                    }
                }
            ]
        })
 
        db = DataBaseProvider(conf)
      
        #todo: Remove the below line it only dumps the data when server starts. kept for debugging
        # alerts_storage.add_data()
        alerts_repository = AlertRepository(db)
        alerts_service = AlertsAppService(alerts_repository)
        usl_service = UslService()

        CsmRestApi.init(alerts_service, usl_service)
        pm = import_plugin_module('alert')

        CsmAgent.alert_monitor = AlertMonitorService(alerts_repository,
                                              pm.AlertPlugin(),
                                              CsmAgent._push_alert)

        #Stats service creation
        time_series_provider = TimelionProvider(const.AGGREGATION_RULE)
        time_series_provider.init()
        CsmRestApi._app["stat_service"] = StatsAppService(time_series_provider)

        #S3 Plugin creation
        s3 = import_plugin_module('s3').S3Plugin()
        CsmRestApi._app["s3_iam_users_service"] = IamUsersService(s3)

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
                print("CSM agent started with pid %d" %pid)
                os._exit(0)


        except OSError as e:
            print("Unable to fork.\nerror(%d): %s" % (e.errno, e.strerror))
            os._exit(1)

        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))

    @staticmethod
    def run(port):
        if not opt.debug:
            CsmAgent._daemonize()
        CsmAgent.alert_monitor.start()
        CsmRestApi.run(port)
        CsmAgent.alert_monitor.stop()

    @staticmethod
    def _push_alert(alert):
        return CsmRestApi.push(alert)

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '..', '..', '..'))
    opt = Opt(sys.argv)
    try:
        from csm.common.log import Log

        log_path = "." if opt.debug else "/var/log/csm"
        Log.init("csm_agent", log_path)
    except:
        print("Can not initialize csm.common.log.Log")
        os._exit(1)

    try:
        from csm.common.conf import Conf
        from csm.common.payload import Yaml
        from csm.core.blogic import const
        from csm.core.services.alerts import AlertsAppService, \
                                            AlertMonitorService, AlertRepository
        from csm.core.services.stats import StatsAppService
        from csm.core.services.s3.iam_users import IamUsersService
        from csm.core.services.usl import UslService
        from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
        from csm.core.agent.api import CsmRestApi

        from csm.common.timeseries import TimelionProvider
        from csm.core.data.db.elasticsearch_db.storage import ElasticSearchDB

        CsmAgent.init()
        CsmAgent.run(const.CSM_AGENT_PORT)
    except Exception as e:
        raise e
        Log.error(traceback.format_exc())
        os._exit(1)
