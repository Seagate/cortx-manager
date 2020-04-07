#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          schemas.py
 Description:       This file contains validation schemas common to multiple controllers

 Creation Date:     03/09/2020
 Author:            Udayan Yaragattikar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

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


class HotFixFileFieldSchema(IsoFileFieldSchema):
    """ Validation schema for uploaded files"""

    pass


class FirmwareUpdateFileFieldSchema(BinFileFieldSchema):
    """Valdation schmea for firmware update"""

    pass
