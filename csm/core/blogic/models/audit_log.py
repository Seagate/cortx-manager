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

import time
from schematics.types import DateTimeType, IntType, StringType, UUIDType
from csm.core.blogic.models import CsmModel

class CsmAuditLogModel(CsmModel):
    """ Model for csm audit logs """
    timestamp = DateTimeType()
    user = StringType(default="")
    remote_ip = StringType(default="")
    forwarded_for_ip = StringType(default="")
    method = StringType(default="")
    path = StringType(default="")
    user_agent = StringType(default="")
    response_code = IntType(default=-1)
    request_id = UUIDType()
    payload = StringType(default="")

class S3AuditLogModel(CsmModel):
    """ Model for s3 audit logs """
    timestamp = DateTimeType()
    authentication_type = StringType(default="")
    bucket = StringType(default="")
    bucket_owner = StringType(default="")
    bytes_received = IntType(default=-1)
    bytes_sent = IntType(default=-1)
    cipher_suite = StringType(default="")
    error_code = StringType(default="")
    host_header = StringType(default="")
    host_id = StringType(default="")
    http_status = IntType(default=-1)
    key = StringType(default="")
    object_size = IntType(default=-1)
    operation = StringType(default="")
    referrer = StringType(default="")
    remote_ip = StringType(default="")
    request_uri = StringType(default="")
    request_id = StringType(default="")
    requester = StringType(default="")
    signature_version = StringType(default="")
    time = StringType(default="")
    total_time = IntType(default=-1)
    turn_around_time = IntType(default=-1)
    user_agent = StringType(default="")
    version_id = StringType(default="")
