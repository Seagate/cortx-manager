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

from .errors import CsmInternalError


class Template:
    """
    Currently this class is just a wrapper over a standard Python's formatting utilities.

    Later it might be modified to support more advanced templating features.
    """

    def __init__(self, raw_template: str):
        self.template = raw_template

    @classmethod
    def from_file(cls, file_name: str):
        try:
            with open(file_name, 'r') as file:
                return cls(file.read())
        except IOError:
            raise CsmInternalError(f'Cannot read from {file_name}') from None

    def render(self, **kwargs):
        return self.template.format(**kwargs)
