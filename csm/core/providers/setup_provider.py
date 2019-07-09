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
        # TODO- Load all configuration file
        self._init_list = {
            "ha": cluster
        }

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
                for component in self._init_list.values():
                    component.init(self._force)
            return Response(0, 'CSM initalized successfully !!!')
        except Exception as e:
            raise CsmError(errno.EINVAL, 'Error: %s' % e)
