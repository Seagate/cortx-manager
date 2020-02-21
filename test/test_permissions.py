from csm.test.common import assert_equal
from csm.common.permission_names import Resource, Action
from csm.core.services.permissions import PermissionSet


def test_permissions_union(*args):
    lhs = PermissionSet({
        Resource.ALERT: {Action.LIST, Action.UPDATE},
        Resource.USER: {Action.CREATE, Action.DELETE, Action.UPDATE},
        Resource.S3USER: {Action.LIST}
    })
    rhs = PermissionSet({
        Resource.ALERT: {Action.CREATE, Action.LIST},
        Resource.USER: {Action.LIST, Action.CREATE, Action.DELETE},
        Resource.STAT: {Action.LIST}
    })

    calculated = lhs | rhs

    expected = PermissionSet({
        Resource.ALERT: {Action.UPDATE, Action.LIST, Action.CREATE},
        Resource.USER: {Action.UPDATE, Action.CREATE, Action.LIST, Action.DELETE},
        Resource.S3USER: {Action.LIST},
        Resource.STAT: {Action.LIST}
    })

    assert_equal(calculated, expected)


def test_permissions_intersection(*args):
    lhs = PermissionSet({
        Resource.ALERT: {Action.LIST, Action.UPDATE},
        Resource.USER: {Action.CREATE, Action.DELETE, Action.UPDATE},
        Resource.S3USER: {Action.LIST}
    })
    rhs = PermissionSet({
        Resource.ALERT: {Action.CREATE, Action.LIST},
        Resource.USER: {Action.LIST, Action.CREATE, Action.DELETE},
        Resource.STAT: {Action.LIST}
    })

    calculated = lhs & rhs

    expected = PermissionSet({
        Resource.ALERT: {Action.LIST},
        Resource.USER: {Action.CREATE, Action.DELETE}
    })

    assert_equal(calculated, expected)


def init(args):
    pass


test_list = [
    test_permissions_union,
    test_permissions_intersection,
]
