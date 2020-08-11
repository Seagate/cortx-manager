"""
 ****************************************************************************
 Filename:          usl.py
 Description:       Models for USL

 Creation Date:     12/17/2019
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from schematics.types import UUIDType, StringType, IntType
from schematics.transforms import blacklist
from uuid import UUID

from csm.core.blogic.models import CsmModel


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
