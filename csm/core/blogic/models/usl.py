"""
 ****************************************************************************
 Filename:          usl.py
 Description:       Contains USL related models

 Creation Date:     11/19/2019
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from uuid import UUID
from dataclasses import dataclass

@dataclass
class Device:
    name: str
    productID: str
    serialNumber: str
    type: str
    uuid: UUID
    vendorID: str

@dataclass
class Volume:
    deviceUuid: UUID
    filesystem: str
    size: int
    used: int
    uuid: UUID

@dataclass
class MountResponse:
    handle: str
    mountPath: str
    bucketName: str



