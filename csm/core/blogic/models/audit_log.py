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
from schematics.models import Model
from schematics.types import DateTimeType, IntType, StringType
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
    response_code = StringType(default="")
    request_id = IntType(default=int(time.time()))
    msg = StringType(min_length=0, default="")

class S3AuditLogModel(CsmModel):
    """ Model for s3 audit logs """
    timestamp = DateTimeType()
    authentication_type = StringType()
    bucket = StringType()
    bucket_owner = StringType()
    bytes_received = StringType()
    bytes_sent = StringType()
    cipher_suite = StringType()
    error_code = StringType()
    host_header = StringType()
    host_id = StringType() 
    http_status = StringType()
    key = StringType()
    object_size = StringType()
    operation = StringType()
    referrer = StringType()
    remote_ip = StringType()
    request_uri = StringType()
    request_id = StringType()
    requester = StringType()
    signature_version = StringType()
    time = StringType()
    total_time = StringType()
    turn_around_time = StringType()
    user_agent = StringType()
    version_id = StringType()

