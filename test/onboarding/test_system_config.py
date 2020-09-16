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
import uuid
from importlib import import_module

from cortx.utils.data.db.db_provider import DataBaseProvider, GeneralConfig

from csm.common.conf import Conf
from csm.common.payload import Yaml
from csm.common.template import Template
from csm.core.blogic import const
from csm.core.services.security import SecurityService
from csm.core.services.system_config import SystemConfigAppService, SystemConfigManager
from csm.test.common import Const

t = unittest.TestCase()
file_path = Const.MOCK_PATH


def _read_system_config_json(test_type):
    """utility function to read test data from json file"""
    if test_type == "create":
        with open(f"{file_path}system_config.json") as system_config_file:
            return json.load(system_config_file)
    else:
        with open(f"{file_path}update_system_config.json") as system_config_file:
            return json.load(system_config_file)


async def _create_system_config(system_config_service):
    """create system config"""
    data = _read_system_config_json("create")
    return await system_config_service.create_system_config(str(uuid.uuid4()), **data)


async def _update_system_config(system_config_service, config_id):
    """update system config"""
    data = _read_system_config_json("update")
    return await system_config_service.update_system_config(config_id, data)


async def _test_delete_system_config(system_config_service, config_id):
    expected_output = {}
    actual_output = await system_config_service.delete_system_config(config_id)
    t.assertEqual(actual_output, expected_output)


async def _test_get_system_config(system_config_service, config_id):
    expected_output = _read_system_config_json("create")
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
    """test initialization"""
    conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
    db = DataBaseProvider(conf)
    params = {
        "username": const.NON_ROOT_USER,
        "password": const.NON_ROOT_USER_PASS
    }
    product = Conf.get(const.CSM_GLOBAL_INDEX, "PRODUCT.name") or 'eos'
    provisioner = import_module(
        f'csm.plugins.{product}.{const.PROVISIONER_PLUGIN}').ProvisionerPlugin(**params)
    system_config_mngr = SystemConfigManager(db)
    security_service = SecurityService(db, provisioner)
    system_config_service = SystemConfigAppService(
        provisioner, security_service, system_config_mngr,
        Template.from_file(const.CSM_SMTP_TEST_EMAIL_TEMPLATE_REL))
    loop = asyncio.get_event_loop()
    args["system_config_service"] = system_config_service
    args["loop"] = loop


def test_get_all_update_system_config(args):
    """test for get and update"""
    loop = args["loop"]
    system_config_service = args["system_config_service"]
    loop.run_until_complete(_test_get_all_system_config(system_config_service))
    system_config = loop.run_until_complete(_create_system_config(system_config_service))
    loop.run_until_complete(
        _test_update_system_config(system_config_service, system_config.get("config_id")))
    loop.run_until_complete(
        _test_delete_system_config(system_config_service, system_config.get("config_id")))


def test_create_system_config(args):
    """test for create system config"""
    loop = args["loop"]
    system_config_service = args["system_config_service"]
    system_config = loop.run_until_complete(_test_create_system_config(system_config_service))
    loop.run_until_complete(
        _test_get_system_config(system_config_service, system_config.get("config_id")))
    loop.run_until_complete(
        _test_delete_system_config(system_config_service, system_config.get("config_id")))


test_list = [test_create_system_config, test_get_all_update_system_config]
