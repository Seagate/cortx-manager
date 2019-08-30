#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          errors.py
 _description:      Errors for various CLI related scenarios.

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import inspect

CSM_OPERATION_SUCESSFUL     = "csm_success"
CSM_ERR_INVALID_VALUE       = "csm_invalid_file"
CSM_ERR_INTERRUPTED         = "csm_interrupted"
CSM_INVALID_REQUEST         = "csm_invalid_request"
CSM_PROVIDER_NOT_AVAILABLE  = "csm_no_provider"
CSM_INTERNAL_ERROR          = "csm_internal_error"

class CsmError(Exception):
    """ Parent class for the cli error classes """

    _rc = CSM_OPERATION_SUCESSFUL
    _desc = 'Operation Successful'
    _caller = ''

    def __init__(self, rc=None, desc=None):
        super(CsmError, self).__init__()
        self._caller = inspect.stack()[1][3]
        if rc is not None: 
            self._rc = str(rc)
        self._desc = desc or self._desc

    def rc(self):
        return self._rc

    def error(self):
        return self._desc

    def caller(self):
        return self._caller

    def __str__(self):
        return "error(%s): %s" % (self._rc, self._desc)

class CommandTerminated(KeyboardInterrupt):
    """
    This error will be raised when some command is terminated during
    the processing
    """

    _err = CSM_ERR_INTERRUPTED
    _desc = "Command is cancelled"

    def __init__(self, _desc=None):
        super(CommandTerminated, self).__init__(_err, _desc)

class InvalidRequest(CsmError):
    """
    This error will be raised when an invalid response
    message is received for any of the cli commands.
    """

    _err = CSM_INVALID_REQUEST
    _desc = "Invalid request message received."

    def __init__(self, _desc=None):
        super(InvalidRequest, self).__init__(_desc)

class CsmInternalError(CsmError):
    """
    This error is raised by CLI for all unknown internal errors
    """

    def __init__(self, desc=None):
        super(CsmInternalError, self).__init__(
            CSM_INTERNAL_ERROR, 'Internal error: %s' %desc)

class CsmNotFoundError(CsmError):
    pass
