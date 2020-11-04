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
import json
import unittest

from csm.common.payload import Json, Payload
from csm.core.services.alerts import AlertRepository, AlertsAppService
from csm.test.common import Const

t = unittest.TestCase()
file_path = Const.MOCK_PATH


def _read_health_summary_json():
    """utility function to read test data from json file"""
    with open(f"{file_path}health_summary_output.json") as health_summary_output:
        return json.load(health_summary_output)


def init(args):
    """test initialization"""
    repo = AlertRepository(None)
    health_schema = Payload(Json(Const.HEALTH_SCHEMA))
    repo.health_schema = health_schema._data
    service = AlertsAppService(repo)
    loop = asyncio.get_event_loop()
    args["service"] = service
    args["loop"] = loop


def test_fetch_health_summary(args):
    """test for fetch health summary"""
    loop = args["loop"]
    service = args["service"]
    actual_output = loop.run_until_complete(service.fetch_health_summary())
    expected_output = _read_health_summary_json()
    t.assertEqual(actual_output, expected_output)


test_list = [test_fetch_health_summary]
