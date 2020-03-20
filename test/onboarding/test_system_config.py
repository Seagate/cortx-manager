#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_system_config.py
 description:       System Config tests

 Creation Date:     16/12/2019
 Author:            Ajay Shingare

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
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.core.services.system_config import SystemConfigAppService, SystemConfigManager
from csm.core.data.db.db_provider import DataBaseProvider, GeneralConfig
from csm.test.common import Const

t = unittest.TestCase()
file_path = Const.MOCK_PATH

def _read_system_config_json(test_type):
    """ utility function to read test data from json file"""
    if test_type == "create":
        with open(file_path + "system_config.json") as system_config_file:
            return json.load(system_config_file)
    else:
        with open(file_path + "update_system_config.json") as system_config_file:
            return json.load(system_config_file)

async def _create_system_config(system_config_service):
    """ create system config"""
    data = _read_system_config_json("create")
    return await system_config_service.create_system_config(str(uuid.uuid4()), **data)

async def _update_system_config(system_config_service, config_id):
    """ update system config """
    data = _read_system_config_json("update")
    return await system_config_service.update_system_config(config_id, data)

async def _test_delete_system_config(system_config_service, config_id):
    expected_output = {}
    actual_output = await system_config_service.delete_system_config(config_id)
    t.assertEqual(actual_output, expected_output)

async def _test_get_system_config(system_config_service, config_id):
    expected_output =  _read_system_config_json("create")
    actual_output = await system_config_service.get_system_config_by_id(config_id)
    actual_output.pop("config_id")
    t.assertEqual(actual_output, expected_output)

async def _test_get_all_system_config(system_config_service):
    expected_output = []
    actual_output = await system_config_service.get_system_config_list()
    t.assertEqual(type(actual_output), type(expected_output))

async def _test_create_system_config(system_config_service):
    expected_output = _read_system_config_json("create")
    actual_output = await _create_system_config(system_config_service)
    config_id = actual_output.pop("config_id")
    t.assertEqual(actual_output, expected_output)
    actual_output["config_id"] = config_id
    return actual_output

async def _test_update_system_config(system_config_service, config_id):
    expected_output = _read_system_config_json("update")
    actual_output = await _update_system_config(system_config_service, config_id)
    config_id = actual_output.pop("config_id")
    t.assertEqual(actual_output, expected_output)

def init(args):
    """ test initialization """
    conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
    db = DataBaseProvider(conf)
    system_config_mngr = SystemConfigManager(db)
    system_config_service = SystemConfigAppService(system_config_mngr)
    loop = asyncio.get_event_loop()
    args["system_config_service"] = system_config_service
    args["loop"] = loop

def test_get_all_update_system_config(args):
    """ test for get and update """
    loop = args["loop"]
    system_config_service = args["system_config_service"]
    loop.run_until_complete(_test_get_all_system_config(system_config_service))
    system_config = loop.run_until_complete(_create_system_config(system_config_service))
    loop.run_until_complete(_test_update_system_config(system_config_service, system_config.get("config_id")))
    loop.run_until_complete(_test_delete_system_config(system_config_service, system_config.get("config_id")))

def test_create_system_config(args):
    """ test for create system config """
    loop = args["loop"]
    system_config_service = args["system_config_service"]
    system_config = loop.run_until_complete(_test_create_system_config(system_config_service))
    loop.run_until_complete(_test_get_system_config(system_config_service, system_config.get("config_id")))
    loop.run_until_complete(_test_delete_system_config(system_config_service, system_config.get("config_id")))

test_list = [test_create_system_config, test_get_all_update_system_config]
