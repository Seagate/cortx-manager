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

from contextlib import contextmanager
from cortx.utils.log import Log
from csm.common.errors import CsmInternalError, CsmPermissionDenied
from csm.core.controllers.view import CsmView, CsmHttpException
from csm.core.services.sessions import S3Credentials
from csm.core.services.s3.utils import S3ServiceError


S3_SERVICE_ERROR = 0x3000


class S3BaseView(CsmView):
    """
    Simple base class for any S3 view which works with one service
    """

    def __init__(self, request, service_name):
        super().__init__(request)

        self._service = request.app.get(service_name, None)
        if issubclass(type(self.request.session.credentials), S3Credentials):
            self._s3_session = self.request.session.credentials
        else:
            self._s3_session = None
        if self._service is None:
            raise CsmInternalError(desc=f"Invalid service '{service_name}'")

    @contextmanager
    def _guard_service(self):
        try:
            yield None
        except S3ServiceError as error:
            raise CsmHttpException(error.status,
                                   S3_SERVICE_ERROR,
                                   error.code,
                                   error.message,
                                   error.message_args)
        else:
            return


class S3AuthenticatedView(S3BaseView):
    """
    Simple base class for any S3 view which requires S3 credentials
    and works with one service
    """

    def __init__(self, request, service_name):
        super().__init__(request, service_name)
        if self._s3_session is None:
            raise CsmPermissionDenied(desc="Invalid credentials - not S3 Account or IAM User")
