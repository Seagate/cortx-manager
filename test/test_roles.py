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

import os
import json
from aiohttp import web
from unittest.mock import MagicMock

from csm.test.common import (
    Const,
    TestFailed,
    assert_equal,
    assert_raises,
    async_test,
    async_return,
    get_type_name
)
from csm.core.services.roles import RoleManager
from csm.core.services.permissions import PermissionSet

from csm.core.agent.api import CsmRestApi

from csm.core.controllers.login import LoginView, LogoutView
from csm.core.controllers.permissions import (
    CurrentPermissionsView,
    UserPermissionsView
)
from csm.core.controllers.stats import StatsView, StatsPanelListView
from csm.core.controllers.storage_capacity import StorageCapacityView
from csm.core.controllers.users import (
    CsmUsersListView,
    CsmUsersView
)


roles_dict = {
    'manage': {
          'permissions': {
               'alerts': ['list', 'update', 'delete'],
               'stats': ['list', 'delete', 'update'],
               'users': ['create', 'delete', 'update', 'list']
          }
    },
    'monitor': {
          'permissions': {
              'alerts': ['list', 'update'],
              'stats': ['list', 'update'],
              'users': ['list', 'update']
          }
    }
}


async def test_manage_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'users': {'create', 'delete', 'list', 'update'}
    })

    actual_permissions = await role_manager.calc_effective_permissions('manage')

    assert_equal(actual_permissions, expected_permissions)


async def test_manage_roles_with_root(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alerts': {'delete', 'list', 'update'},
        'stats': {'delete', 'list', 'update'},
        'users': {'create', 'delete', 'list', 'update'}
    })

    actual_permissions = await role_manager.calc_effective_permissions('admin', 'manage')

    assert_equal(actual_permissions, expected_permissions)


async def test_monitor_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alerts': {'list', 'update'},
        'stats': {'list', 'update'},
        'users': {'list', 'update'}
    })

    actual_permissions = await role_manager.calc_effective_permissions('monitor')

    assert_equal(actual_permissions, expected_permissions)


async def test_invalid_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet()

    actual_permissions = await role_manager.calc_effective_permissions('nfs')

    assert_equal(actual_permissions, expected_permissions)


CSM_BASE_DIRS = [
    os.path.join(os.path.dirname(__file__), '..'),
    Const.CSM_PATH,
]

def open_schema_file(filename, mode='r'):
    """ Helper function for opening file either from the directory
        with the source code or from global installation path """

    for basepath in CSM_BASE_DIRS:
        fullpath = os.path.join(basepath, 'schema', filename)
        try:
            return open(fullpath, mode)
        except OSError:
            pass
    raise TestFailed(f'Can\'t open file {filename}')


async def check_rest_ep_permissions(role_manager, handler, method, roles, must_fail):
    """ Helper function for testing one REST API endpoint using a list of roles """

    async def null_handler(request):
        return None

    request = MagicMock()
    request.method = method
    request.match_info.handler = handler
    request.app.router.resolve.return_value = async_return(request.match_info)
    request.session.permissions = PermissionSet()

    if roles:
        request.session.permissions = \
            await role_manager.calc_effective_permissions(*roles)

    try:
        if must_fail:
            with assert_raises(web.HTTPForbidden):
                await CsmRestApi.permission_middleware(request, null_handler)
        else:
            await CsmRestApi.permission_middleware(request, null_handler)
    except Exception as e:
        handler_name = get_type_name(handler)
        raise TestFailed(f'{handler_name}: {method} as {roles} -- {e}')


class Method:
    """ HTTP method names """

    GET = 'GET'
    DELETE = 'DELETE'
    PATCH = 'PATCH'
    POST = 'POST'
    PUT = 'PUT'


class User:
    """ Typical users with predefined roles """

    Anon = None
    CsmAdmin = 'admin'
    CsmUser = 'monitor'
    S3Account = 's3'


class Access:
    """ Access verdict constants """

    OK = True
    FAIL = False


async def test_rest_ep_permissions(*args):
    """ Check an accessibiliy of all REST API endpoints using predefined roles """

    with open_schema_file('roles.json') as f:
        predefined_roles = json.load(f)

    role_manager = RoleManager(predefined_roles)

    rest_ep_cases = [

        (LoginView                , Method.POST  , User.Anon     , Access.OK  ),
        (LoginView                , Method.POST  , User.CsmAdmin , Access.OK  ),
        (LoginView                , Method.POST  , User.CsmUser  , Access.OK  ),
        (LoginView                , Method.POST  , User.S3Account, Access.OK  ),

        (LogoutView               , Method.POST  , User.Anon     , Access.OK  ),
        (LogoutView               , Method.POST  , User.CsmAdmin , Access.OK  ),
        (LogoutView               , Method.POST  , User.CsmUser  , Access.OK  ),
        (LogoutView               , Method.POST  , User.S3Account, Access.OK  ),

        (CurrentPermissionsView   , Method.GET   , User.Anon     , Access.FAIL),
        (CurrentPermissionsView   , Method.GET   , User.CsmAdmin , Access.OK  ),
        (CurrentPermissionsView   , Method.GET   , User.CsmUser  , Access.OK  ),
        (CurrentPermissionsView   , Method.GET   , User.S3Account, Access.OK  ),

        (UserPermissionsView      , Method.GET   , User.Anon     , Access.FAIL),
        (UserPermissionsView      , Method.GET   , User.CsmAdmin , Access.OK  ),
        (UserPermissionsView      , Method.GET   , User.CsmUser  , Access.OK  ),
        (UserPermissionsView      , Method.GET   , User.S3Account, Access.OK  ),

        (StatsView                , Method.GET   , User.Anon     , Access.FAIL),
        (StatsView                , Method.GET   , User.CsmAdmin , Access.OK  ),
        (StatsView                , Method.GET   , User.CsmUser  , Access.OK  ),
        (StatsView                , Method.GET   , User.S3Account, Access.FAIL),

        (StatsPanelListView       , Method.GET   , User.Anon     , Access.FAIL),
        (StatsPanelListView       , Method.GET   , User.CsmAdmin , Access.OK  ),
        (StatsPanelListView       , Method.GET   , User.CsmUser  , Access.OK  ),
        (StatsPanelListView       , Method.GET   , User.S3Account, Access.FAIL),

        (StorageCapacityView      , Method.GET   , User.Anon     , Access.FAIL),
        (StorageCapacityView      , Method.GET   , User.CsmAdmin , Access.OK  ),
        (StorageCapacityView      , Method.GET   , User.CsmUser  , Access.OK  ),
        (StorageCapacityView      , Method.GET   , User.S3Account, Access.FAIL),

        (CsmUsersListView         , Method.GET   , User.Anon     , Access.FAIL),
        (CsmUsersListView         , Method.GET   , User.CsmAdmin , Access.OK  ),
        (CsmUsersListView         , Method.GET   , User.CsmUser  , Access.OK  ),
        (CsmUsersListView         , Method.GET   , User.S3Account, Access.FAIL),
        (CsmUsersListView         , Method.POST  , User.Anon     , Access.FAIL),
        (CsmUsersListView         , Method.POST  , User.CsmAdmin , Access.OK  ),
        (CsmUsersListView         , Method.POST  , User.CsmUser  , Access.FAIL),
        (CsmUsersListView         , Method.POST  , User.S3Account, Access.FAIL),

        (CsmUsersView             , Method.GET   , User.Anon     , Access.FAIL),
        (CsmUsersView             , Method.GET   , User.CsmAdmin , Access.OK  ),
        (CsmUsersView             , Method.GET   , User.CsmUser  , Access.OK  ),
        (CsmUsersView             , Method.GET   , User.S3Account, Access.FAIL),
        (CsmUsersView             , Method.PATCH , User.Anon     , Access.FAIL),
        (CsmUsersView             , Method.PATCH , User.CsmAdmin , Access.OK  ),
        (CsmUsersView             , Method.PATCH , User.CsmUser  , Access.FAIL),
        (CsmUsersView             , Method.PATCH , User.S3Account, Access.FAIL),
        (CsmUsersView             , Method.DELETE, User.Anon     , Access.FAIL),
        (CsmUsersView             , Method.DELETE, User.CsmAdmin , Access.OK  ),
        (CsmUsersView             , Method.DELETE, User.CsmUser  , Access.FAIL),
        (CsmUsersView             , Method.DELETE, User.S3Account, Access.FAIL),
    ]

    for handler, method, roles, access in rest_ep_cases:
        await check_rest_ep_permissions(role_manager, handler,
                                        method, roles, not access)


def init(args):
    pass


test_list = [
    async_test(test_manage_roles),
    async_test(test_monitor_roles),
    async_test(test_manage_roles_with_root),
    async_test(test_invalid_roles),
    async_test(test_rest_ep_permissions),
]
