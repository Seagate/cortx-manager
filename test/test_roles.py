from csm.test.common import assert_equal, async_test
from csm.core.services.roles import RoleManager
from csm.core.services.permissions import PermissionSet


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
              'users': ['list']
          }
    }
}


async def test_manage_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alerts': {'delete', 'list', 'update'},
        'stats': {'delete', 'list', 'update'},
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

    actual_permissions = await role_manager.calc_effective_permissions('root', 'manage')

    assert_equal(actual_permissions, expected_permissions)


async def test_monitor_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alerts': {'list', 'update'},
        'stats': {'list', 'update'},
        'users': {'list'}
    })

    actual_permissions = await role_manager.calc_effective_permissions('monitor')

    assert_equal(actual_permissions, expected_permissions)


async def test_invalid_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet()

    actual_permissions = await role_manager.calc_effective_permissions('nfs')

    assert_equal(actual_permissions, expected_permissions)


def init(args):
    pass


test_list = [
    async_test(test_manage_roles),
    async_test(test_monitor_roles),
    async_test(test_manage_roles_with_root),
    async_test(test_invalid_roles),
]

