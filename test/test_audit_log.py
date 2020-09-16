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

import asyncio
import unittest

from csm.core.services.audit_log import AuditService

t = unittest.TestCase()


class MockAuditManager():
    async def retrieve_by_range(self, *args, **kwargs):
        return []

    async def count_by_range(self, *args, **kwargs):
        return 0


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
    expected_value = "csm.12-02-2020.17-02-2020"
    t.assertIn(expected_value, actual_value)


def test_filename_service():
    mock_mngr = MockAuditManager()
    audit_service = AuditService(mock_mngr)
    actual_value = audit_service.generate_audit_log_filename("csm", 1581490848, 1581922908)
    expected_value = "csm.12-02-2020.17-02-2020"
    t.assertIn(expected_value, actual_value)


def run_tests():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_show_audit_log_service())
    loop.run_until_complete(test_download_audit_log_service())
    test_filename_service()


test_list = [run_tests]
