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

from uuid import uuid4
from datetime import datetime
from schematics.models import Model
from schematics.types import UUIDType, StringType, IntType, DateTimeType, ModelType
from schematics.transforms import blacklist

from eos.utils.db import BaseModel

class Device(BaseModel):
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


class Volume(BaseModel):
    """
    Class depicts device's Volume model for USL
    """

    _id = "uuid"

    name = StringType()
    bucketName = StringType()
    deviceUuid = UUIDType()
    filesystem = StringType()
    size = IntType()
    used = IntType()
    uuid = UUIDType()

    class Options:
        """
        Class describes fields visibility Options for Volume objects during serialization
        """

        roles = {'public' : blacklist('bucketName')}

    @staticmethod
    def instantiate(name, bucketName, deviceUuid, uuid, filesystem='s3', size=0, used=0):
        """
        Creates a volume instance
        """

        v = Volume()
        v.name = name
        v.bucketName = bucketName
        v.deviceUuid = deviceUuid
        v.uuid = uuid
        v.filesystem = filesystem
        v.size = size
        v.used = used
        return v


class Event(BaseModel):
    """
    Base class for all USL Events
    """

    _id = "event_id"

    event_id = UUIDType()
    name = StringType()
    date = DateTimeType()

    class Options:
        """
        Class describes Event visibility options for Event objects during serialization
        """

        roles = {'public' : blacklist('event_id')}


class NewVolumeEvent(Event):
    """
    Class depicts new volume event model for USL
    """

    volume = ModelType(Volume)

    @staticmethod
    def instantiate(volume, name="NewVolumeEvent", event_id=uuid4(), date=datetime.now()):
        """
        Creates an instance of NewVolumeEvent
        """

        nve = NewVolumeEvent()
        nve.name = name
        nve.volume = volume
        nve.event_id = event_id
        nve.date = date
        return nve


class VolumeRemovedEvent(Event):
    """
    Class depicts volume removed event model for USL
    """

    uuid = UUIDType()

    @staticmethod
    def instantiate(uuid, name="VolumeRemovedEvent", event_id=uuid4(), date=datetime.now()):
        """
        Creates an instance of VolumeRemovedEvent
        """

        vre = VolumeRemovedEvent()
        vre.name = name
        vre.uuid = uuid
        vre.event_id = event_id
        vre.date = date
        return vre


# Let MountResponse inherit just Model:
# It'll very unlikely be stored in db, so doesn't need PK
class MountResponse(Model):
    """
    Class depicts the Mount Response for USL's mount volume request
    """

    handle = StringType()
    mountPath = StringType()

    @staticmethod
    def instantiate(handle, mountPath):
        """
        Creates an instance of MountResponse
        """

        mr = MountResponse()
        mr.handle = handle
        mr.mountPath = mountPath
        return mr
