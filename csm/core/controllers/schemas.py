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

from marshmallow import Schema, fields, validate
from csm.core.services.file_transfer import FileType, FileCache, FileRef
from csm.core.controllers.validators import FileRefValidator, PackageFilenameValidator


class FileFieldSchema(Schema):
    """ Validation schema for uploaded files"""
    content_type = fields.Str(required=True)
    filename = fields.Str(validate=PackageFilenameValidator(), required=True)
    file_ref = fields.Field(validate=FileRefValidator())
