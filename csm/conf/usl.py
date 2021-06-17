#!/bin/env python3

# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

import traceback
import os
import pwd
from cortx.utils.log import Log
from cortx.utils.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_pkg import PkgV
from cortx.utils.validator.v_confkeys import ConfKeysV
from cortx.utils.validator.v_network import NetworkV
from cortx.utils.validator.v_path import PathV
from datetime import datetime
from csm.common.process import SimpleProcess


class UslSetupError(Exception):
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


class Usl:
    """ Represents Usl and Performs setup related actions """
    CONSUMER_INDEX = "consumer"
    USL_GLOBAL_INDEX = "usl"
    USL_CONF_PATH = "/opt/seagate/cortx/csm/conf/etc/csm/usl.conf"

    def __init__(self, conf_url):
        Conf.init()
        Conf.load(Usl.CONSUMER_INDEX, conf_url)
        Conf.load(Usl.USL_GLOBAL_INDEX, f"yaml://{Usl.USL_CONF_PATH}")
        Log.init(service_name = "usl_setup", log_path = "/tmp",
                level="INFO")
        self.machine_id = Usl._get_machine_id()
        self.server_node_info = f"server_node>{self.machine_id}"
        self.conf_store_keys = {}

    def validate_pkgs(self):
        Log.info("Validating third party rpms")
        PkgV().validate("rpms", ["uds-pyi"])

    def validate_cert_paths(self):
        Log.info("Validating certificate paths")
        cert_base_path = Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["crt_path_key"])
        PathV().validate('exists', [
            f"dir:{cert_base_path}",
            f"file:{os.path.join(cert_base_path, Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys['native_crt']))}",
            f"file:{os.path.join(cert_base_path, Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys['native_key']))}"
        ])

    def _prepare_and_validate_confstore_keys(self, phase: str):
        """ Perform validtions. Raises exceptions if validation fails """
        if phase == "post_install":
            self.conf_store_keys.update({
                "csm_user_key": "cortx>software>csm>user"
                })
        elif phase == "prepare":
            self.conf_store_keys.update({
                "server_node_info":self.server_node_info,
                "data_public_fqdn":f"{self.server_node_info}>network>data>public_fqdn",
                "cluster_id":f"{self.server_node_info}>cluster_id",
            })
        elif phase == "config":
            self.conf_store_keys.update({
                "crt_path_key":"cortx>software>uds>certificate_path",
                "domain_crt":"cortx>software>uds>domain_crt",
                "domain_key":"cortx>software>uds>domain_key",
                "native_crt":"cortx>software>uds>native_crt",
                "native_key":"cortx>software>uds>native_key",
            })
        elif phase == "post_upgrade":
            self.conf_store_keys.update({
                "csm_user_key": "cortx>software>csm>user",
                "server_node_info":self.server_node_info,
                "data_public_fqdn":f"{self.server_node_info}>network>data>public_fqdn",
                "cluster_id":f"{self.server_node_info}>cluster_id",
                "crt_path_key":"cortx>software>uds>certificate_path",
                "domain_crt":"cortx>software>uds>domain_crt",
                "domain_key":"cortx>software>uds>domain_key",
                "native_crt":"cortx>software>uds>native_crt",
                "native_key":"cortx>software>uds>native_key",
            })

        self._validate_conf_store_keys(Usl.CONSUMER_INDEX)
        return 0

    def _validate_conf_store_keys(self, index, keylist=None):
        if not keylist:
            keylist = list(self.conf_store_keys.values())
        if not isinstance(keylist, list):
            raise UslSetupError(rc=-1, message="Keylist should be kind of list")
        Log.info(f"Validating confstore keys: {keylist}")
        ConfKeysV().validate("exists", index, keylist)

    @staticmethod
    def _get_machine_id():
        """
        Obtains current minion id. If it cannot be obtained, returns default node #1 id.
        """
        Log.info("Fetching Machine Id.")
        cmd = "cat /etc/machine-id"
        machine_id, _err, _returncode = Usl._run_cmd(cmd)
        if _returncode != 0:
            raise UslSetupError(rc=_returncode,message='Unable to obtain current machine id.')
        return machine_id.replace("\n", "")

    @staticmethod
    def _run_cmd(cmd):
        """
        Run command and throw error if cmd failed
        """

        _err = ""
        Log.info(f"Executing cmd: {cmd}")
        _proc = SimpleProcess(cmd)
        _output, _err, _rc = _proc.run(universal_newlines=True)
        Log.info(f"Output: {_output}, \n Err:{_err}, \n RC:{_rc}")
        if _rc != 0:
            raise UslSetupError(rc=_rc,message=f'Obtained non-zero response count for cmd: {cmd} Error: {_err} ')
        return _output, _err, _rc

    def _create_config_backup(self):
        if os.path.exists("/etc/csm"):
            Log.info("Creating backup for older csm configurations")
            Usl._run_cmd(f"cp -r /etc/csm /etc/csm_{str(datetime.now()).replace(' ','T').split('.')[0]}_bkp")
        else:
            os.makedirs("/etc/csm", exist_ok=True)
            Usl._run_cmd("cp -r /opt/seagate/cortx/csm/conf/etc/csm /etc/csm")

    def post_install(self):
        """ Performs post install operations. Raises exception on error """
        csm_user = Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["csm_user_key"])
        Conf.set(Usl.USL_GLOBAL_INDEX, 'PROVISIONER>username', csm_user)
        self.create()
        return 0

    def prepare(self):
        """ Performs post install operations. Raises exception on error """
        cluster_id = Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["cluster_id"])
        virtual_host_key = f'cluster>{cluster_id}>network>management>virtual_host'
        self._validate_conf_store_keys(Usl.CONSUMER_INDEX,[virtual_host_key])
        virtual_host = Conf.get(Usl.CONSUMER_INDEX, virtual_host_key)
        data_nw_public_fqdn = Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["data_public_fqdn"] )
        try:
            NetworkV().validate('connectivity', [virtual_host, data_nw_public_fqdn])
        except Exception as e:
            raise UslSetupError(rc=-1, message="Network Validation failed.")
        Conf.set(Usl.USL_GLOBAL_INDEX, 'PROVISIONER>cluster_id', cluster_id)
        Conf.set(Usl.USL_GLOBAL_INDEX, 'PROVISIONER>virtual_host', virtual_host)
        Conf.set(Usl.USL_GLOBAL_INDEX, 'PROVISIONER>node_public_data_domain_name', data_nw_public_fqdn)

        self.create()
        return 0

    def config(self):
        """ Performs configurations. Raises exception on error """
        self.validate_cert_paths()
        Conf.set(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>cert_path',
                Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["crt_path_key"]))
        Conf.set(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>domain_crt',
                Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["domain_crt"]))
        Conf.set(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>domain_key',
                Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["domain_key"]))
        Conf.set(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>native_crt',
                Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["native_crt"]))
        Conf.set(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>native_key',
                Conf.get(Usl.CONSUMER_INDEX, self.conf_store_keys["native_key"]))
        self.create()
        return 0

    def init(self):
        """ Perform initialization. Raises exception on error """
        self._set_service_user()
        self._config_user()
        cert_path = Conf.get(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>cert_path_key')
        Usl._run_cmd(f"chmod 700 {cert_path}")
        for each_cert in [
            Conf.get(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>native_crt'),
            Conf.get(Usl.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>native_key')
        ]:
            Usl._run_cmd(f"chmod 600 {cert_path}/{each_cert}")
            Usl._run_cmd(f"chown {self._user}:{self._user} {cert_path}/{each_cert}")
        return 0


    def pre_upgrade(self):
        """ Performs Pre upgrade functionalitied. Raises exception on error """

        # TODO: Perform actual steps. Obtain inputs using Conf.get(index, ..)
        return 0

    def post_upgrade(self):
        """ Performs Post upgrade functionalitied. Raises exception on error """
        self._create_config_backup()
        self.validate_pkgs()
        self.post_install()
        self.prepare()
        self.config()
        self.init()
        return 0

    def test(self, plan):
        """ Perform configuration testing. Raises exception on error """

        # TODO: Perform actual steps. Obtain inputs using Conf.get(index, ..)
        return 0

    def reset(self):
        """ Performs Configuraiton reset. Raises exception on error """

        # TODO: Perform actual steps. Obtain inputs using Conf.get(index, ..)
        return 0

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """
        Log.info("Creating CSM Conf File on Required Location.")
        Conf.save(Usl.USL_GLOBAL_INDEX)
        os.makedirs("/etc/csm", exist_ok=True)
        Usl._run_cmd(f"cp -rn {Usl.USL_CONF_PATH} /etc/csm/")

    def _set_service_user(self):
        """
        This Method will set the username for service user to Self._user
        :return:
        """
        self._user = Conf.get(Usl.USL_GLOBAL_INDEX, 'PROVISIONER>username')

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

    def _config_user(self):
        """
        Check user already exist and create if not exist
        If reset true then delete user
        """
        if not self._is_user_exist():
            Log.info("Creating CSM User without password.")
            Usl._run_cmd((f"useradd -M {self._user}"))
            Log.info("Adding CSM User to Wheel Group.")
            Usl._run_cmd(f"usermod -aG wheel {self._user}")
            Log.info("Enabling nologin for CSM user.")
            Usl._run_cmd(f"usermod -s /sbin/nologin {self._user}")
            if not self._is_user_exist():
                Log.error("Csm User Creation Failed.")
                raise UslSetupError(rc=-1, message=f"Unable to create {self._user} user")
        else:
            Log.info(f"User {self._user} already exist")