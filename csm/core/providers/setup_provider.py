#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          setup_provider.py
 Description:       Setup Provider for csm

 Creation Date:     05/08/2019
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
import pwd
import crypt
import errno
from csm.common.errors import CsmError
from csm.common.log import Log
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.core.providers.providers import Provider, Request, Response

class SetupProvider(Provider):
    """ Provider implementation for csm initialization """

    def __init__(self, cluster):
        super(SetupProvider, self).__init__(const.CSM_SETUP_CMD, cluster)
        self._user = const.NON_ROOT_USER
        self._password = crypt.crypt(const.NON_ROOT_USER_PASS, "22")
        self._uid = self._gid = -1
        self._bundle_path = Conf.get(const.CSM_GLOBAL_INDEX,
            const.SUPPORT_BUNDLE_ROOT, const.DEFAULT_SUPPORT_BUNDLE_ROOT)
        self._init_list = {
            "ha": cluster
        }

    def _is_user_exist(self):
        ''' Check if user exists '''
        try:
            u = pwd.getpwnam(self._user)
            self._uid = u.pw_uid
            self._gid = u.pw_gid
            return True
        except KeyError as err:
            return False

    def _config_user(self):
        ''' create user and allow permission for csm resources '''
        if not self._is_user_exist():
            os.system("useradd -p "+self._password+" "+ self._user)
            if not self._is_user_exist():
                raise CsmError(-1, "Unable to create %s user" % self._user)
        os.makedirs(self._bundle_path, exist_ok=True)
        os.chown(self._bundle_path, self._uid, self._gid)
        os.system("setfacl -m u:" + self._user + ":rwx /var/log/csm/csm.log")
        os.system("setfacl -m u:" + self._user + ":rwx /var/log/messages")

    def _validate_request(self, request):
        self._actions = const.CSM_SETUP_ACTIONS
        self._action = request.action()
        self._force = True if 'force' in request.args() else False

        if self._action not in self._actions:
            raise CsmError(errno.EINVAL, 'Invalid Action %s' % self._action)

        if len(request.args()) > 1 and 'force' not in request.args():
            raise CsmError(errno.EINVAL, 'Invalid Option %s' % request.args())

    def _process_request(self, request):
        try:
            if self._action == "init":
                self._config_user()
                for component in self._init_list.values():
                    component.init(self._force)
            return Response(0, 'CSM initalized successfully !!!')
        except Exception as e:
            raise CsmError(errno.EINVAL, 'Error: %s' % e)
