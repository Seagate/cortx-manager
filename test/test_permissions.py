from csm.test.common import assert_equal
from csm.common.permission_names import Resource, Action
from csm.core.services.permissions import PermissionSet


def test_permissions_union(*args):
    lhs = PermissionSet({
        Resource.ALERTS: {Action.LIST, Action.UPDATE},
        Resource.USERS: {Action.CREATE, Action.DELETE, Action.UPDATE},
        Resource.S3IAMUSERS: {Action.LIST}
    })
    rhs = PermissionSet({
        Resource.ALERTS: {Action.CREATE, Action.LIST},
        Resource.USERS: {Action.LIST, Action.CREATE, Action.DELETE},
        Resource.STATS: {Action.LIST}
    })

    calculated = lhs | rhs

    expected = PermissionSet({
        Resource.ALERTS: {Action.UPDATE, Action.LIST, Action.CREATE},
        Resource.USERS: {Action.UPDATE, Action.CREATE, Action.LIST, Action.DELETE},
        Resource.S3IAMUSERS: {Action.LIST},
        Resource.STATS: {Action.LIST}
    })

    assert_equal(calculated, expected)


def test_permissions_intersection(*args):
    lhs = PermissionSet({
        Resource.ALERTS: {Action.LIST, Action.UPDATE},
        Resource.USERS: {Action.CREATE, Action.DELETE, Action.UPDATE},
        Resource.S3IAMUSERS: {Action.LIST}
    })
    rhs = PermissionSet({
        Resource.ALERTS: {Action.CREATE, Action.LIST},
        Resource.USERS: {Action.LIST, Action.CREATE, Action.DELETE},
        Resource.STATS: {Action.LIST}
    })

    calculated = lhs & rhs

    expected = PermissionSet({
        Resource.ALERTS: {Action.LIST},
        Resource.USERS: {Action.CREATE, Action.DELETE}
    })

    assert_equal(calculated, expected)


def init(args):
    pass


test_list = [
    test_permissions_union,
    test_permissions_intersection,
]
