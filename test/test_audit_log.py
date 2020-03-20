#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_audit_log.py
 description        unit test for audit log

 Creation Date:     20/02/2020
 Author:            Mazhar Inamdar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio
import sys
import os
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.core.services.audit_log import AuditService, AuditLogManager
from csm.common.errors import CsmPermissionDenied
from csm.core.data.db.db_provider import DataBaseProvider, GeneralConfig
from csm.common.queries import DateTimeRange
t = unittest.TestCase()

class MockAuditManager():

    async def retrieve_by_range(self, *args, **kwargs):
        return []

    async def count_by_range(self, *args, **kwargs):
        return 0

def init(args):
    pass

async def test_show_audit_log_service():
    mock_mngr = MockAuditManager()
    audit_service = AuditService(mock_mngr)
    actual_value = await audit_service.get_by_range("csm", 1581490848, 1581922908)
    expected_value = []
    t.assertEqual(actual_value, expected_value)

async def test_download_audit_log_service():
    mock_mngr = MockAuditManager()
    audit_service = AuditService(mock_mngr)
    actual_value = await audit_service.get_audit_log_zip("csm", 1581490848, 1581922908)
    expected_value = "csm_1581490848_1581922908.tar.gz"
    t.assertEqual(actual_value, expected_value)

def test_filename_service():
    mock_mngr = MockAuditManager()
    audit_service = AuditService(mock_mngr)
    actual_value = audit_service.generate_audit_log_filename("csm", 1581490848, 1581922908)
    expected_value = "csm_1581490848_1581922908"
    t.assertEqual(actual_value, expected_value)

def run_tests(args = {}):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_show_audit_log_service())
    loop.run_until_complete(test_download_audit_log_service())
    test_filename_service()

test_list = [run_tests]
			 
