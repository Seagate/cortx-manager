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

from marshmallow import Schema, fields
from csm.core.controllers.validators import (FileRefValidator, IsoFilenameValidator, 
                                             BinFilenameValidator)


class FileFieldSchema(Schema):
    """ Validation schema for uploaded files"""
    content_type = fields.Str(required=True)
    filename = fields.Str(required=True)
    file_ref = fields.Field(validate=FileRefValidator())


class IsoFileFieldSchema(Schema):
    """Base File Filed validator for 'iso'-uploaded files"""
    content_type = fields.Str(required=True)
    filename = fields.Str(validate=IsoFilenameValidator(), required=True)
    file_ref = fields.Field(validate=FileRefValidator())

class BinFileFieldSchema(Schema):
    """Base File Filed validator for 'bin'-uploaded files"""
    content_type = fields.Str(required=True)
    filename = fields.Str(validate=BinFilenameValidator(), required=True)
    file_ref = fields.Field(validate=FileRefValidator())
