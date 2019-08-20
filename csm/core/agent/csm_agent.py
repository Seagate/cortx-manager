#!/usr/bin/env python3

from aiohttp import web
import sys
import os
import traceback

# Global options for debugging purposes
# It is quick and dirty temporary solution
class Opt:
    def __init__(self, argv):
        self.debug = len(argv) > 1 and argv[1] == '--debug'

global opt

class CsmAgent:
    """ CSM Core Agent / Deamon """

    @staticmethod
    def init():
        Conf.init()
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
        CsmRestApi.init()
        """ Starting Alert Monitor """
        alert_monitor = AlertMonitor()
        alert_monitor.start()

    @staticmethod
    def _daemonize():
        """ Change process into background service """

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
        CsmRestApi.run(port)

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
        from csm.core.blogic import const
        from csm.common.payload import *
        from csm.core.agent.api import CsmRestApi
        from csm.core.blogic.alerts.alerts import AlertMonitor

        CsmAgent.init()
        CsmAgent.run(const.CSM_AGENT_PORT)

    except:
        Log.error(traceback.format_exc())
        os._exit(1)
