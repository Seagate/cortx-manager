from csm.test.common import assert_equal, async_test
from csm.core.services.roles import RoleManager
from csm.core.services.permissions import PermissionSet


roles_dict = {
    'manage': {
          'permissions': {
               'alert': ['list', 'update', 'delete'],
               'stat': ['list', 'delete', 'update'],
               'user': ['create', 'delete', 'update', 'list']
          }
    },
    'monitor': {
          'permissions': {
              'alert': ['list', 'update'],
              'stat': ['list', 'update'],
              'user': ['list']
          }
    }
}


async def test_manage_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alert': {'delete', 'list', 'update'},
        'stat': {'delete', 'list', 'update'},
        'user': {'create', 'delete', 'list', 'update'}
    })

    actual_permissions = await role_manager.calc_effective_permissions('manage')

    assert_equal(actual_permissions, expected_permissions)


async def test_manage_roles_with_root(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alert': {'delete', 'list', 'update'},
        'stat': {'delete', 'list', 'update'},
        'user': {'create', 'delete', 'list', 'update'}
    })

    actual_permissions = await role_manager.calc_effective_permissions('root', 'manage')

    assert_equal(actual_permissions, expected_permissions)


async def test_monitor_roles(*args):
    role_manager = RoleManager(roles_dict)
    expected_permissions = PermissionSet({
        'alert': {'list', 'update'},
        'stat': {'list', 'update'},
        'user': {'list'}
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

