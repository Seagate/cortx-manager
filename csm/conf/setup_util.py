# Common utility file for cli-setup  and csm-setup
# Can be copied to cli/conf directory at the time of build generation
import os
from cortx.utils.conf_store.conf_store import Conf
from csm.common.payload import Text
from os import stat
import pwd
import traceback
from cortx.utils.log import Log
from cortx.utils.process import SimpleProcess
from cortx.utils.validator.error import VError

from cortx.utils.validator.v_confkeys import ConfKeysV
from cortx.utils.validator.v_pkg import PkgV


class Const:
    BASE_PATH = "/opt/seagate/cortx/"
    CSM = "csm"
    CSM_BASE_PATH = BASE_PATH + CSM
    CSM_GLOBAL_INDEX = 'CSM'
    INVENTORY_INDEX = 'INVENTORY'
    DATABASE_INDEX = 'DATABASE'
    CONSUMER_INDEX = 'CONSUMER'
    TEST_INDEX = 'TEST'

    SRC_CONFIG_DIR = CSM_BASE_PATH + "/conf/etc/"
    CSM_SRC_CONFIG_DIR = SRC_CONFIG_DIR + CSM
    REQ_TXT_PATH = CSM_BASE_PATH + "/conf/requirment.txt"
    EDGE_INSTALL_TYPE ={ "nodes": 1,
                    "servers_per_node": 2,
                    "storage_type": ["5u84", "PODS", "RBOD"],
                    "server_type": "physical"}
    RSYSLOG_DIR = "/etc/rsyslog.d"
    SOURCE_RSYSLOG_PATH = f"{CSM_BASE_PATH}/conf/{RSYSLOG_DIR}/0-csm_logs.conf"
    LOGROTATE_DIR = "/etc/logrotate.d"
    SOURCE_LOGROTATE_PATH = f"{CSM_BASE_PATH}/conf/{LOGROTATE_DIR}/csm_agent_log.conf"
    LOGROTATE_AMOUNT_VIRTUAL = 3
    ES_CLEANUP_PERIOD_VIRTUAL = 2
    CRON_DIR = "/etc/cron.daily"
    SOURCE_CRON_PATH = f"{CSM_BASE_PATH}/conf{CRON_DIR}/es_logrotate.cron"
    DEST_CRON_PATH = f"{CRON_DIR}/es_logrotate.cron"
    CSM_TMP_FILE_CACHE_DIR = '/tmp/csm/file_cache/transfer'


    #Cluster admin creds
    DEFAULT_CLUSTER_ADMIN_USER = 'cortxadmin'
    DEFAULT_CLUSTER_ADMIN_PASS = 'Cortxadmin@123'
    DEFAULT_CLUSTER_ADMIN_EMAIL = 'cortxadmin@seagate.com'


class CsmSetupError(Exception):
    """ Generic Exception with error code and output """

    def __init__(self, rc, message, *args):
        self._rc = rc
        self._desc = message % (args)

    def __str__(self):
        if self._rc == 0: return self._desc
        return "error(%d): %s\n\n%s" %(self._rc, self._desc,
            traceback.format_exc())

    @property
    def rc(self):
        return self._rc

class Setup_Util:

    @staticmethod
    def _validate_conf_store_keys(index, keylist=None):
        if not isinstance(keylist, list):
            raise CsmSetupError(rc=-1, message="Keylist should be kind of list")
        Log.info(f"Validating confstore keys: {keylist}")
        ConfKeysV().validate("exists", index, keylist)

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

    @staticmethod
    def _is_user_exist(_user):
        """
        Check if user exists
        """
        try:
            u = pwd.getpwnam(_user)
            _uid = u.pw_uid
            _gid = u.pw_gid
            return True
        except KeyError as err:
            return False

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
    def _update_csm_files(key, value):
        """
        Update CSM Files Depending on Job Type of Setup.
        """
        Log.info(f"Update file for {key}:{value}")
        CSM_SERVICE_FILE =  "/etc/systemd/system/csm_agent.service"
        service_file_data = Text(CSM_SERVICE_FILE).load()
        data = service_file_data.replace(key, value)
        Text(CSM_SERVICE_FILE).dump(data)

    @staticmethod
    def _set_csm_conf_path(self):
        conf_path = Conf.get(Const.CONSUMER_INDEX, "cortx>software>csm>conf_path",
                                                     Const.CORTX_CONFIG_DIR)
        conf_path = os.path.join(conf_path, Const.CSM)
        if not os.path.exists(conf_path):
            os.makedirs(conf_path, exist_ok=True)
        Log.info(f"Setting Config saving path:{conf_path} from confstore")
        return conf_path