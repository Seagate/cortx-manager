#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          audit_log.py
 Description:       Contains the csm and s3 model.

 Creation Date:     31/01/2020
 Author:            Mazhar Inamdar 

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from schematics.models import Model
from schematics.types import DateType, StringType, DateTimeType
from csm.core.blogic.models import CsmModel

class CsmAuditLogModel(CsmModel):
    """ Model for csm audit logs """
    message = StringType()
    timestamp = DateTimeType()

class S3AuditLogModel(CsmModel):
    """ Model for s3 audit logs """
    timestamp = DateTimeType()
    authentication_type = StringType()
    bucket = StringType()
    bucket_owner = StringType()
    bytes_received = StringType()
    bytes_sent = StringType()
    cipher_suite = StringType()
    error_code = StringType()
    host_header = StringType()
    host_id = StringType() 
    http_status = StringType()
    key = StringType()
    object_size = StringType()
    operation = StringType()
    referrer = StringType()
    remote_ip = StringType()
    request_uri = StringType()
    request_id = StringType()
    requester = StringType()
    signature_version = StringType()
    time = StringType()
    total_time = StringType()
    turn_around_time = StringType()
    user_agent = StringType()
    version_id = StringType()

