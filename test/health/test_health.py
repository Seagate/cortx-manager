#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_health.py
 description:       System Health tests

 Creation Date:     02/19/2020
 Author:            Soniya Moholkar

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
import json
import unittest
import uuid
from csm.common.payload import Json, Payload
from csm.core.services.alerts import AlertsAppService, AlertRepository
from csm.test.common import Const

t = unittest.TestCase()
file_path = Const.MOCK_PATH

def _read_health_summary_json():
    """ utility function to read test data from json file"""
    with open(file_path + "health_summary_output.json") as health_summary_output:
        return json.load(health_summary_output)
    

def init(args):
    """ test initialization """
    repo = AlertRepository(None)
    health_schema = Payload(Json(Const.HEALTH_SCHEMA))
    repo.health_schema = health_schema._data
    service = AlertsAppService(repo)
    loop = asyncio.get_event_loop()
    args["service"] = service
    args["loop"] = loop

def test_fetch_health_summary(args):
    """ test for fetch health summary """
    loop = args["loop"]
    service = args["service"]
    actual_output = loop.run_until_complete(service.fetch_health_summary())
    expected_output = _read_health_summary_json()
    t.assertEqual(actual_output, expected_output)    

test_list = [test_fetch_health_summary]
