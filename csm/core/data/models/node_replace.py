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

from datetime import datetime, timezone
from schematics.types import StringType, DateTimeType, IntType
from csm.core.blogic.models.base import CsmModel


class ReplaceNode(CsmModel):
    _id = "job_id"

    node_id = StringType()
    job_id = StringType()
    status = StringType()
    hostname = StringType()
    ssh_port = IntType()
    created_time = DateTimeType()
    updated_time = DateTimeType()

    @staticmethod
    def generate_new(job_id, node_id, hostname, ssh_port):
        """

        :param job_id:
        :param node_id:
        :return:
        """
        replace_node_obj = ReplaceNode()
        replace_node_obj.job_id = job_id
        replace_node_obj.node_id = node_id
        replace_node_obj.hostname = hostname
        replace_node_obj.ssh_port = ssh_port
        replace_node_obj.status = JobStatus.Is_Running
        replace_node_obj.created_time = datetime.now(timezone.utc)
        replace_node_obj.updated_time = datetime.now(timezone.utc)
        return replace_node_obj


class JobStatus:
    """
    Repository Class for Node Replacement.
    """
    Is_Running = "Running"
    Completed = "Completed"
    Not_Running = "Not Running"

