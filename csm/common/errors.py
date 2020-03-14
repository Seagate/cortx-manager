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

from csm.common.log import Log

CSM_OPERATION_SUCESSFUL     = 0x0000
CSM_ERR_INVALID_VALUE       = 0x1001
CSM_ERR_INTERRUPTED         = 0x1002
CSM_INVALID_REQUEST         = 0x1003
CSM_PROVIDER_NOT_AVAILABLE  = 0x1004
CSM_INTERNAL_ERROR          = 0x1005
CSM_SETUP_ERROR             = 0x1006
CSM_RESOURCE_EXIST          = 0x1007

class CsmError(Exception):
    """ Parent class for the cli error classes """

    _rc = CSM_OPERATION_SUCESSFUL
    _desc = 'Operation Successful'
    _caller = ''

    def __init__(self, rc=0, desc=None, message_id=None, message_args=None):
        super(CsmError, self).__init__()
        self._caller = inspect.stack()[1][3]
        if rc is not None:
            self._rc = str(rc)
        self._desc = desc or self._desc
        self._message_id = message_id
        self._message_args = message_args
        # TODO: Log.error message will be changed when desc is removed and
        #  improved exception handling is implemented.
        # TODO: self._message_id will be formatted with self._message_args
        # Common error logging for all kind of CsmError
        Log.error(f"{self._rc}:{self._desc}:{self._message_id}:{self._message_args}")

    def message_id(self):
        return self._message_id

    def message_args(self):
        return self._message_args

    def rc(self):
        return self._rc

    def error(self):
        return self._desc

    def caller(self):
        return self._caller

    def __str__(self):
        return "error(%s): %s" % (self._rc, self._desc)

class CsmSetupError(CsmError):
    """
    This error will be raised when csm setup is failed
    """
    _desc = "Csm Setup is failed"

    def __init__(self, _desc=None):
        super(CsmSetupError, self).__init__(CSM_SETUP_ERROR, _desc)

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

    def __init__(self, _desc=None, message_id=None, message_args=None):
        super(InvalidRequest, self).__init__(
            CSM_INVALID_REQUEST, _desc, message_id, message_args)


class ResourceExist(CsmError):
    """
    This error will be raised when an resource already exist
    """

    _err = CSM_RESOURCE_EXIST
    _desc = "Resource already exist."

    def __init__(self, _desc=None, message_id=None, message_args=None):
        super(ResourceExist, self).__init__(
            CSM_RESOURCE_EXIST, _desc, message_id, message_args)


class CsmInternalError(CsmError):
    """
    This error is raised by CLI for all unknown internal errors
    """

    def __init__(self, desc=None, message_id=None, message_args=None):
        super(CsmInternalError, self).__init__(
            CSM_INTERNAL_ERROR, 'Internal error: %s' % desc,
            message_id, message_args)


class CsmNotFoundError(CsmError):
    """
    This error is raised for all cases when an entity was not found
    """

    def __init__(self, desc=None, message_id=None, message_args=None):
        super(CsmNotFoundError, self).__init__(
            CSM_INTERNAL_ERROR, desc,
            message_id, message_args)

class CsmPermissionDenied(CsmError):
    """
    This error is raised for all cases when we don't have permissions
    """

    def __init__(self, desc=None, message_id=None, message_args=None):
        super(CsmPermissionDenied, self).__init__(
            CSM_INTERNAL_ERROR, desc,
            message_id, message_args)

class DataAccessError(CsmInternalError):

    """Base Data Access Error"""


class DataAccessExternalError(DataAccessError):

    """Internal DB errors which happen outside of CSM"""


class DataAccessInternalError(DataAccessError):

    """Errors regarding CSM part of Data Access implementation"""


class MalformedQueryError(DataAccessError):

    """Malformed Query or Filter error"""


class MalformedConfigurationError(DataAccessError):

    """Error in configuration of data bases or storages or db drivers"""


class StorageNotFoundError(DataAccessError):

    """Model object is not associated with any storage"""
