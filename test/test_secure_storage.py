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

import sys
import os
import asyncio
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from eos.utils.security.cipher import Cipher
from eos.utils.security.secure_storage import SecureStorage
from csm.common.payload import Yaml
from csm.core.blogic import const
from eos.utils.data.db.db_provider import DataBaseProvider, GeneralConfig

t = unittest.TestCase()


def init(args):
    conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
    db = DataBaseProvider(conf)
    key = Cipher.generate_key('test', 'secure', 'storage')

    args['loop'] = asyncio.get_event_loop()
    args['secure_storage'] = SecureStorage(db, key)


def test_store_get_delete(args):
    loop = args['loop']
    storage = args['secure_storage']
    test_name = 'test_secure_storage'
    test_data = b'test_data'
    loop.run_until_complete(storage.store(test_name, test_data))
    data = loop.run_until_complete(storage.get(test_name))
    t.assertEqual(data, test_data)
    loop.run_until_complete(storage.delete(test_name))
    data = loop.run_until_complete(storage.get(test_name))
    t.assertIsNone(data)


test_list = [test_store_get_delete]
