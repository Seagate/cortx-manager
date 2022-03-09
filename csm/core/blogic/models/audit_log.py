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
    response_code = IntType(default=-1)
    request_id = IntType(default=int(time.time()))
    payload = StringType(default="")
