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

from cortx.utils.data.db.db_provider import DataBaseProvider, GeneralConfig
from csm.core.services.users import CsmUserService, UserManager
from csm.common.errors import InvalidRequest, CsmNotFoundError
from csm.core.blogic import const
from csm.common.payload import Yaml
import asyncio
import sys
import os
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

t = unittest.TestCase()


def init(args):
    conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
    db = DataBaseProvider(conf)
    usrmngr = UserManager(db)
    user_service = CsmUserService(usrmngr)
    loop = asyncio.get_event_loop()
    args['user_service'] = user_service
    args['loop'] = loop


def test_csm_user_create(args):
    loop = args['loop']
    user_service = args.get('user_service')
    data = {'user_id': 'csm_test_manage_user',
            'password': 'Csmuser@123',
            'user_role': 'manage',
            'email_address': 'csm@test.com',
            'alert_notification': True}

    # Better replace with local dict storage to avoid this
    try:
        args['user'] = loop.run_until_complete(
            user_service.get_user(data['user_id']))
    except Exception:
        args['user'] = loop.run_until_complete(
            user_service.create_user(**data))

    user = loop.run_until_complete(user_service.get_user(data['user_id']))
    assert 'updated_time' in user
    assert 'created_time' in user
    assert user['username'] == data['user_id']
    assert user['user_role'] == data['user_role']
    assert user['email_address'] == data['email_address']
    assert user['alert_notification'] == data['alert_notification']


def test_csm_user_update_without_current_password(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'anything': 'anything'}

    # We can't update user without current_password
    with t.assertRaises(InvalidRequest) as e:
        loop.run_until_complete(
            user_service.update_user(user_id, data, user_id))
    assert 'Value for current_password is required' in str(e.exception)


def test_csm_user_update_password(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'password': 'Csmuser@123New',
            'current_password': 'Csmuser@123'}
    loop.run_until_complete(user_service.update_user(user_id, data, user_id))

    # We can't update password anymore with same old_password
    with t.assertRaises(InvalidRequest):
        loop.run_until_complete(
            user_service.update_user(user_id, data, user_id))

    data = {'password': 'Csmuser@123',
            'current_password': 'Csmuser@123New'}

    # But when we set a new password, we can
    loop.run_until_complete(user_service.update_user(user_id, data, user_id))


def test_csm_user_update_roles(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'user_role': 'monitor',
            'current_password': 'Csmuser@123'}

    # Initial roles set
    user = loop.run_until_complete(user_service.get_user(user_id))
    assert user['user_role'] == 'manage'

    loop.run_until_complete(
        user_service.update_user(user_id, data, 'csm_test_user'))

    # New roles set
    user = loop.run_until_complete(user_service.get_user(user_id))
    assert user['user_role'] == 'monitor'


def test_csm_user_update_email(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'email_address': 'csmnew@test.com' ,
            'current_password': 'Csmuser@123'}

    # Initial email
    user = loop.run_until_complete(user_service.get_user(user_id))
    assert user['email_address'] == 'csm@test.com'

    loop.run_until_complete(
        user_service.update_user(user_id, data, 'csm_test_user'))

    # New email
    user = loop.run_until_complete(user_service.get_user(user_id))
    assert user['email_address'] == 'csmnew@test.com'


def test_csm_user_update_alert_notification(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    data = {'alert_notification': False ,
            'current_password': 'Csmuser@123'}

    # Initial alert_notification
    user = loop.run_until_complete(user_service.get_user(user_id))
    assert user['alert_notification'] == True

    loop.run_until_complete(
        user_service.update_user(user_id, data, 'csm_test_user'))

    # New alert_notification
    user = loop.run_until_complete(user_service.get_user(user_id))
    assert user['alert_notification'] == False


def test_csm_user_delete(args):
    loop = args['loop']
    user_service = args.get('user_service')

    user_id = args.get('user').get('id')
    loop.run_until_complete(user_service.delete_user(user_id, user_id))
    with t.assertRaises(CsmNotFoundError) as e:
        loop.run_until_complete(user_service.get_user(user_id))
    assert 'User does not exist' in str(e.exception)


test_list = [test_csm_user_create,
             test_csm_user_update_without_current_password,
             test_csm_user_update_password,
             test_csm_user_update_roles,
             test_csm_user_update_email,
             test_csm_user_update_alert_notification,
             test_csm_user_delete]
