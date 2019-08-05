#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          init_provider.py
 Description:       Init Provider for csm initalization

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
from csm.common import const
from csm.core.providers.providers import Provider, Request, Response

from csm.core.blogic.csm_ha import CsmHA

class InitProvider(Provider):
    """ Provider implementation for csm initialization """

    _init_list = {
        "ha": CsmHA
    }

    def __init__(self, cluster):
        super(InitProvider, self).__init__(const.CSM_INIT_CMD, cluster)
        # TODO- Load all configuration file
        self._actions = list(self._init_list.keys())

    def _validate_request(self, request):
        self._action = request.action()
        self._args = request.args()
        if self._action not in self._actions + ["all"]:
            raise CsmError(errno.EINVAL, 'Invalid Action %s' % self._action)

    def _process_request(self, request):
        _output = ''
        try:
            if self._action == "all":
                for component in self._init_list.values():
                    csm_component = component(self._args)
                    _output = csm_component.init()
            else:
                csm_component = self._init_list[self._action](self._args)
                _output = csm_component.init()
            return Response(0, _output)
        except Exception as e:
            raise CsmError(errno.EINVAL, 'Error: %s' % e)
