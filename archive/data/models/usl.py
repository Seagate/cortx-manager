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

from schematics.types import BooleanType, IPv4Type, IntType, MACAddressType, StringType, UUIDType
from schematics.transforms import blacklist

# TODO: Replace with non-offensive term when possible. An issue was sent on 08/24/2020
# to https://github.com/schematics/schematics/issues/613 requesting this.

from csm.core.blogic.models import CsmModel
from uuid import UUID
from typing import Optional


class NetIface(CsmModel):
    _id = 'macAddress'

    name = StringType(required=True, min_length=1)
    mac_address = MACAddressType(required=True, serialized_name='macAddress')
    iface_type = StringType(required=True, serialized_name='type')
    is_active = BooleanType(required=True, serialized_name='isActive')
    is_loopback = BooleanType(required=True, serialized_name='isLoopback')
    ipv4 = IPv4Type()
    netmask = StringType()
    broadcast = StringType()

    @staticmethod
    def instantiate(
        name: str,
        mac_address: str,
        iface_type: str,
        is_active: bool,
        is_loopback: bool,
        ipv4: Optional[str] = None,
        netmask: Optional[str] = None,
        broadcast: Optional[str] = None,
    ) -> 'NetIface':
        i = NetIface()
        i.name = name
        i.mac_address = mac_address
        i.iface_type = iface_type
        i.is_active = is_active
        i.is_loopback = is_loopback
        if ipv4 is not None:
            i.ipv4 = ipv4
        if netmask is not None:
            i.netmask = netmask
        if broadcast is not None:
            i.broadcast = broadcast
        return i


class Device(CsmModel):
    """
    Class depicts Device model for USL
    """

    _id = "uuid"

    name = StringType()
    productID = StringType()
    serialNumber = StringType()
    type = StringType()
    uuid = UUIDType()
    vendorID = StringType()

    @staticmethod
    def instantiate(name, productID, serialNumber, type, uuid, vendorID):
        """
        Creates a Device instance
        """

        d = Device()
        d.name = name
        d.productID = productID
        d.serialNumber = serialNumber
        d.type = type
        d.uuid = uuid
        d.vendorID = vendorID
        return d


class Volume(CsmModel):
    """
    Class depicts device's Volume model for USL
    """

    _id = "uuid"

    name = StringType()
    bucketName = StringType()
    deviceUuid = UUIDType()
    uuid = UUIDType()
    size = IntType()
    used = IntType()
    filesystem = StringType()

    class Options:
        """
        Class describes fields visibility Options for Volume objects during serialization
        """

        roles = {'public': blacklist('bucketName')}
        # TODO: Replace with non-offensive term when possible. An issue was sent on 08/24/2020
        # to https://github.com/schematics/schematics/issues/613 requesting this.


    @staticmethod
    def instantiate(
        name: str,
        bucketName: str,
        deviceUuid: UUID,
        uuid: UUID,
        size: int,
        used: int,
        filesystem: str = 's3',
    ) -> 'Volume':
        """
        Creates a volume instance
        """

        v = Volume()
        v.name = name
        v.bucketName = bucketName
        v.deviceUuid = deviceUuid
        v.uuid = uuid
        v.size = size
        v.used = used
        v.filesystem = filesystem
        v.validate()
        return v


class ApiKey(CsmModel):
    """
    Represents the USL API key
    """

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
