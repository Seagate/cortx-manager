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

from uuid import UUID

from schematics.transforms import blacklist

# TODO: Replace with non-offensive term when possible. An issue was sent on 08/24/2020
# to https://github.com/schematics/schematics/issues/613 requesting this.

from schematics.types import IntType, StringType, UUIDType

from csm.core.blogic.models import CsmModel


class Device(CsmModel):
    """Class depicts Device model for USL"""
    _id = "uuid"
    name = StringType()
    product_id = StringType()
    serial_number = StringType()
    type = StringType()
    uuid = UUIDType()
    vendor_id = StringType()

    @staticmethod
    def instantiate(name, product_id, serial_number, type_par, uuid, vendor_id):
        """Creates a Device instance"""
        d = Device()
        d.name = name
        d.product_id = product_id
        d.serial_number = serial_number
        d.type = type_par
        d.uuid = uuid
        d.vendor_id = vendor_id
        return d


class Volume(CsmModel):
    """Class depicts device's Volume model for USL"""
    _id = "uuid"

    name = StringType()
    bucket_name = StringType()
    device_uuid = UUIDType()
    uuid = UUIDType()
    size = IntType()
    used = IntType()
    filesystem = StringType()

    class Options:
        """Class describes fields visibility Options for Volume objects during serialization"""
        roles = {'public': blacklist('bucketName')}
        # TODO: Replace with non-offensive term when possible. An issue was sent on 08/24/2020
        # to https://github.com/schematics/schematics/issues/613 requesting this.

    @staticmethod
    def instantiate(name: str, bucket_name: str, device_uuid: UUID, uuid: UUID, size: int,
                    used: int, filesystem: str = 's3',) -> 'Volume':
        """Creates a volume instance"""
        v = Volume()
        v.name = name
        v.bucket_name = bucket_name
        v.device_uuid = device_uuid
        v.uuid = uuid
        v.size = size
        v.used = used
        v.filesystem = filesystem
        v.validate()
        return v


class ApiKey(CsmModel):
    """Represents the USL API key"""
    _id = "key"
    key = UUIDType()

    @staticmethod
    def instantiate(key):
        """
        Creates an ApiKey instance
        """

        k = ApiKey()
        k.key = key
        return k
