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

from csm.core.blogic.models.base import CsmModel
from schematics.types import StringType, DateTimeType
from datetime import timezone


class CommentModel(CsmModel):
    comment_id = StringType()
    comment_text = StringType()
    created_time = DateTimeType()
    created_by = StringType()

    def to_primitive(self) -> dict:
        obj = super().to_primitive()

        if self.created_time:
            obj["created_time"] =\
                    int(self.created_time.replace(tzinfo=timezone.utc).timestamp())
        return obj

    def __hash__(self):
        """Returns hash value of the object."""
        return hash(self.comment_id)
