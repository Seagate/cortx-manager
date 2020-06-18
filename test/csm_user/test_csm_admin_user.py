#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_csm_admin_user.py
 description:       Csm admin user tests

 Creation Date:     04/15/2020
 Author:            Artem Obruchnikov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from eos.utils.data.db.db_provider import DataBaseProvider, GeneralConfig
from csm.common.errors import CsmPermissionDenied
from csm.core.services.users import CsmUserService, UserManager
from csm.common.errors import InvalidRequest, CsmPermissionDenied
from csm.core.blogic import const
from csm.common.payload import Yaml
import asyncio
import sys
import os
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

t = unittest.TestCase()

class MockProvisioner():

    async def create_system_user(self, *args, **kwargs):
        return True

def init(args):
    conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
    db = DataBaseProvider(conf)
    usrmngr = UserManager(db)
    provisioner = MockProvisioner()
    user_service = CsmUserService(provisioner, usrmngr)
    loop = asyncio.get_event_loop()
    args['user_service'] = user_service
    args['loop'] = loop


def test_csm_admin_user_create(args):
    loop = args['loop']
    user_service = args.get('user_service')
    data = {'user_id': 'csm_test_user',
            'password': 'Csmuser@123',
            'roles': ['admin']}

    # Better replace with local dict storage to avoid this
    try:
        args['user'] = loop.run_until_complete(
            user_service.get_user(data['user_id']))
    except:
        args['user'] = loop.run_until_complete(
            user_service.create_user(**data))

    user = loop.run_until_complete(user_service.get_user(data['user_id']))
    assert 'updated_time' in user
    assert 'created_time' in user
    assert user['username'] == data['user_id']
    assert user['roles'] == data['roles']


def test_csm_admin_user_update_without_old_password(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'anything': 'anything'}

    # We can't update admin user without old_password
    with t.assertRaises(InvalidRequest) as e:
        loop.run_until_complete(
            user_service.update_user(user_id, data, user_id))
    assert 'Super user old password is required' in str(e.exception)


def test_csm_admin_user_update_password(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'password': 'Csmuser@123New',
            'old_password': 'Csmuser@123'}
    loop.run_until_complete(user_service.update_user(user_id, data, user_id))

    # We can't update password anymore with same old_password
    with t.assertRaises(InvalidRequest):
        loop.run_until_complete(
            user_service.update_user(user_id, data, user_id))

    data = {'password': 'Csmuser@123',
            'old_password': 'Csmuser@123New'}

    # But when we set a new password, we can
    loop.run_until_complete(user_service.update_user(user_id, data, user_id))


def test_csm_admin_user_update_roles(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'roles': ['admin'],
            'old_password': 'Csmuser@123'}

    # We can't update admin user roles
    with t.assertRaises(CsmPermissionDenied) as e:
        loop.run_until_complete(
            user_service.update_user(user_id, data, user_id))
    assert 'Cannot change roles for super user' in str(e.exception)


def test_csm_admin_user_delete(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    with t.assertRaises(CsmPermissionDenied) as e:
        loop.run_until_complete(user_service.delete_user(user_id, user_id))
    assert 'Can\'t delete super user' in str(e.exception)


test_list = [test_csm_admin_user_create,
             test_csm_admin_user_update_without_old_password,
             test_csm_admin_user_update_password,
             test_csm_admin_user_update_roles,
             test_csm_admin_user_delete]
