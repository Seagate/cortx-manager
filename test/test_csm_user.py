#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_csm_user.py
 description:       Csm User tests

 Creation Date:     06/12/2019
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
from csm.core.services.users import CsmUserService, UserManager
from csm.common.errors import CsmPermissionDenied
from csm.core.data.db.db_provider import DataBaseProvider, GeneralConfig

t = unittest.TestCase()

async def _create_csm_user(user_service):
    data = {'user_id':'csm_test_user',
            'password':'Csmuser@123',
            'roles':['root', 'admin']}
    try:
        return await user_service.get_user(data['user_id'])
    except:
        return await user_service.create_user(**data)

async def _update_csm_user(user_service, user_id):
    data = {'roles':['admin']}
    return await user_service.update_user(user_id, data)

async def _test_delete_csm_user(user_service, user_id):
    expected_output = {}
    actual_output = await user_service.delete_user(user_id)
    t.assertEqual(actual_output, expected_output)

async def _test_delete_root_csm_user(user_service, user_id):
    with t.assertRaises(CsmPermissionDenied):
        await user_service.delete_user(user_id)

def init(args):
    conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
    db = DataBaseProvider(conf)
    usrmngr = UserManager(db)
    user_service = CsmUserService(usrmngr)
    loop = asyncio.get_event_loop()
    args['user_service'] = user_service
    args['loop'] = loop

def test_csm_user_delete(args):
    loop = args['loop']
    user_service = args['user_service']
    user = loop.run_until_complete(_create_csm_user(user_service))
    loop.run_until_complete(_test_delete_root_csm_user(user_service, user['id']))
    loop.run_until_complete(_update_csm_user(user_service, user['id']))
    loop.run_until_complete(_test_delete_csm_user(user_service, user['id']))

test_list = [test_csm_user_delete]
