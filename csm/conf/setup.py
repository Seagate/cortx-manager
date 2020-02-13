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
from csm.core.blogic.csm_ha import CsmResourceAgent
from csm.common.ha_framework import PcsHAFramework
from csm.common.cluster import Cluster
from csm.core.agent.api import CsmApi

class Setup:
    def __init__(self):
        self._user = const.NON_ROOT_USER
        self._password = crypt.crypt(const.NON_ROOT_USER_PASS, "22")
        self._uid = self._gid = -1
        self._bundle_path = Conf.get(const.CSM_GLOBAL_INDEX,
            const.SUPPORT_BUNDLE_ROOT, const.DEFAULT_SUPPORT_BUNDLE_ROOT)
        pass

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
        Create user and allow permission for csm resources
        """
        if not self._is_user_exist():
            os.system("useradd -p "+self._password+" "+ self._user)
            if not self._is_user_exist():
                raise CsmError(-1, "Unable to create %s user" % self._user)
        #TODO : replace os.system with subprocess
        #TODO : move hardcoded path to const
        os.system("mkdir -p /var/seagate/eos")
        os.system("setfacl -R -m u:csm:rwx /var/seagate/eos")
        os.system("mkdir -p /etc/csm /var/log/seagate/csm")
        os.system(f"chown -R {self._user}:{self._user} /etc/csm")
        os.system(f"chown -R {self._user}:{self._user} /var/log/seagate/csm")
        os.system("systemctl daemon-reload")
        os.system("systemctl enable csm_agent")
        os.system("systemctl enable csm_web")

    def _load_conf(self):
        """
        Load all configuration file and through error if file is missing
        """
        if not os.path.exists(const.CSM_CONF):
            raise CsmError(-1, "%s file is missing for csm setup" %const.CSM_CONF)
        if not os.path.exists(const.INVENTORY_FILE):
            raise CsmError(-1, "%s file is missing for csm setup" %const.INVENTORY_FILE)
        if not os.path.exists(const.COMPONENTS_CONF):
            raise CsmError(-1, "%s file is missing for csm setup" %const.COMPONENTS_CONF)
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
        Conf.load(const.INVENTORY_INDEX, Yaml(const.INVENTORY_FILE))
        Conf.load(const.COMPONENTS_INDEX, Yaml(const.COMPONENTS_CONF))

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
        #self._cluster.init() #Uncomment this to setup ha resource agent
        CsmApi.set_cluster(self._cluster)

class CsmSetup(Setup):
    def __init__(self):
        super(CsmSetup, self).__init__()
        pass

    def post_install(self, args):
        pass

    def init(self, args):
        """
        Check and move required configuration file
        """
        self._config_user()
        self._load_conf()
        self._config_cluster()
        pass

    def config(self, args):
        pass

    def reset(self, args):
        pass
