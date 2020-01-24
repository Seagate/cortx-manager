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
import sys
import pwd
import errno
from csm.common.errors import CsmError
from csm.common.log import Log
from csm.common.conf import Conf
from csm.conf.setup import CsmSetup
from csm.core.blogic import const
from csm.core.providers.providers import Provider, Request, Response

class SetupProvider(Provider):
    """
    Provider implementation for csm initialization
    """
    def __init__(self):
        super(SetupProvider, self).__init__(const.CSM_SETUP_CMD)
        self._csm_setup = CsmSetup()

    def _validate_request(self, request):
        """
        Validate setup command request
        """
        self._action = request.options["sub_command_name"]

        if self._action == "init" or self._action == "post_install":
            self._force = request.options["f"]
        elif self._action == "reset":
            self._reset_hard = request.options["hard"]

    def _process_request(self, request):
        try:
            arg_list = {}
            if self._action == "init":
                arg_list["force"] = self._force
            elif self._action == "reset":
                arg_list["hard"] = self._reset_hard
            getattr(self._csm_setup, "%s" %(self._action))(arg_list)
            return Response(0, "CSM %s : PASS" %self._action)
        except Exception as e:
            Log.error("CSM setup failed: %s" %e)
            return Response(errno.EINVAL, "CSM %s : Fail" %self._action)
