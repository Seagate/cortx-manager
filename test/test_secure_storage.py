"""
 ****************************************************************************
 Filename:          test_secure_storage.py
 Description:       Test secure storage API.

 Creation Date:     02/20/2020
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
import os
import asyncio
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from eos.utils.security.cipher import Cipher
from eos.utils.security.secure_storage import SecureStorage
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.core.data.db.db_provider import DataBaseProvider, GeneralConfig

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
