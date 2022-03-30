# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

import inspect

from cortx.utils.errors import BaseError
from cortx.utils.log import Log
from csm.core.blogic import const

CSM_OPERATION_SUCESSFUL     = 0x0000
CSM_ERR_INVALID_VALUE       = 0x1001
CSM_ERR_INTERRUPTED         = 0x1002
CSM_INVALID_REQUEST         = 0x1003
CSM_PROVIDER_NOT_AVAILABLE  = 0x1004
CSM_INTERNAL_ERROR          = 0x1005
CSM_SETUP_ERROR             = 0x1006
CSM_RESOURCE_EXIST          = 0x1007
CSM_OPERATION_NOT_PERMITTED = 0x1008
CSM_FAILURE                 = 0x1009
CSM_SERVICE_NOT_AVAILABLE   = 0x100A
CSM_REQUEST_CANCELLED       = 0x100B
CSM_NOT_IMPLEMENTED         = 0x100C
CSM_SERVICE_CONFLICT        = 0x100D
CSM_GATEWAY_TIMEOUT         = 0x100E
CSM_UNAUTHORIZED_ERROR      = 0x100F

class CsmError(BaseError):
    """ Parent class for the cli error classes """

    def __init__(self, rc=0, desc=None, message_id=None, message_args=None):
        super(CsmError, self).__init__(rc=rc, desc=desc, message_id=message_id,
                                       message_args=message_args)
        # TODO: Log.error message will be changed when desc is removed and
        #  improved exception handling is implemented.
        # TODO: self._message_id will be formatted with self._message_args
        # Common error logging for all kind of CsmError
        Log.error(f"{self._rc}:{self._desc}:{self._message_id}:{self._message_args}")


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

    def __init__(self, _desc=None, message_id=const.INVALID_REQUEST, message_args=None):
        super(InvalidRequest, self).__init__(
            CSM_INVALID_REQUEST, _desc, message_id, message_args)


class ResourceExist(CsmError):
    """
    This error will be raised when an resource already exist
    """

    _err = CSM_RESOURCE_EXIST
    _desc = "Resource already exist."

    def __init__(self, _desc=None, message_id=const.RESOURCE_EXISTS, message_args=None):
        super(ResourceExist, self).__init__(
            CSM_RESOURCE_EXIST, _desc, message_id, message_args)


class CsmInternalError(CsmError):
    """
    This error is raised by CLI for all unknown internal errors
    """

    def __init__(self, desc=None, message_id=const.INTERNAL_ERROR, message_args=None):
        super(CsmInternalError, self).__init__(
            CSM_INTERNAL_ERROR, 'Internal error: %s' % desc,
            message_id, message_args)


class CsmNotFoundError(CsmError):
    """
    This error is raised for all cases when an entity was not found
    """

    def __init__(self, desc=None, message_id=const.NOT_FOUND_ERROR, message_args=None):
        super(CsmNotFoundError, self).__init__(
            CSM_INTERNAL_ERROR, desc,
            message_id, message_args)


class CsmPermissionDenied(CsmError):
    """
    This error is raised for all cases when we don't have permissions
    """

    def __init__(self, desc=None, message_id=const.PERMISSION_DENIED_ERROR, message_args=None):
        super(CsmPermissionDenied, self).__init__(
            CSM_OPERATION_NOT_PERMITTED, desc,
            message_id, message_args)


class CsmResourceNotAvailable(CsmInternalError):

    """Describes issues when requested resource is not available"""

    def __init__(self, desc=None, message_id=const.RESOURCE_NOT_AVAILABLE, message_args=None):
        super(CsmResourceNotAvailable, self).__init__(
            desc, message_id, message_args)

class CsmTypeError(CsmInternalError):

    """Issues related to incorrect type of argument/parameter, etc."""

    def __init__(self, desc=None, message_id=const.TYPE_ERROR, message_args=None):
        super(CsmTypeError, self).__init__(
            desc, message_id, message_args)

class CsmNotImplemented(CsmError):

    """This error represents HTTP 501 Not Implemented Error"""

    def __init__(self, desc=None, message_id=const.NOT_IMPLEMENTED, message_args=None):
        super(CsmNotImplemented, self).__init__(
            CSM_NOT_IMPLEMENTED, desc,
            message_id, message_args)

class CsmServiceConflict(CsmError):

    """Service in conflict stat or operation can cause that state"""

    def __init__(self, desc=None, message_id=const.SERVICE_CONFLICT, message_args=None):
        super(CsmServiceConflict, self).__init__(
            CSM_SERVICE_CONFLICT, desc,
            message_id, message_args)

class CsmGatewayTimeout(CsmError):

    """
    This error represents a scenario where CSM was acting as a gateway or proxy and did not receive
    a timely response from the upstream server.
    """

    def __init__(self, desc=None, message_id=const.GATEWAY_TIMEOUT, message_args=None):
        super(CsmGatewayTimeout, self).__init__(
            CSM_GATEWAY_TIMEOUT, desc,
            message_id, message_args)

class CsmUnauthorizedError(CsmError):

    """This error represents HTTP 401 Unauthorized Error"""

    def __init__(self, desc=None, message_id=const.UNAUTHORIZED_ERROR, message_args=None):
        super(CsmUnauthorizedError, self).__init__(
            CSM_UNAUTHORIZED_ERROR, desc,
            message_id, message_args)

class CsmServiceNotAvailable(CsmError):

    """This  error represents CSM service is Not Available."""

    def __init__(self, desc=None, message_id=const.SERVICE_NOT_AVAILABLE, message_args=None):
        super(CsmServiceNotAvailable, self).__init__(
            CSM_SERVICE_NOT_AVAILABLE, desc,
            message_id, message_args)

class CsmRequestCancelled(CsmError):

    """This  error represents CSM service request is cancelled."""

    def __init__(self, desc=None, message_id=const.REQUEST_CANCELLED, message_args=None):
        super(CsmRequestCancelled, self).__init__(
            CSM_REQUEST_CANCELLED, desc,
            message_id, message_args)
