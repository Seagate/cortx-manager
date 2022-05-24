# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
from csm.core.controllers.view import CsmView, CsmHttpException
from csm.core.services.rgw.s3.utils import S3ServiceError
from marshmallow import Schema, ValidationError, validates_schema
from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf

S3_SERVICE_ERROR = 0x3000


class S3BaseSchema(Schema):
    """Base Class for S3 Schema Validation."""

    @validates_schema
    def invalidate_empty_values(self, data, **kwargs):
        """Invalidate the empty strings."""
        for key, value in data.items():
            if value is not None and not str(value).strip():
                raise ValidationError(f"Empty value for {key}")


class S3BaseView(CsmView):
    """Simple base class for any S3 view which works with one service."""

    def __init__(self, request, service_name):
        """Construct S3 Base View."""
        super().__init__(request)
        self._service = self.request.app[service_name]
        self._iam_privileged_user_uid = Conf.get(const.CSM_GLOBAL_INDEX, const.RGW_S3_IAM_ADMIN_USER)

    def _is_iam_privileged_user(self, uid) -> bool:
        """
        Check if uid is of privileged IAM user.

        Args:
            uid (string): uid of an IAM user.

        Returns:
            bool: True if input uid is of privileged IAM user.
        """
        verdict: bool = False
        if uid == self._iam_privileged_user_uid:
            verdict = True
        return verdict

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
