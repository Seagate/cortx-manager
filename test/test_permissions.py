from csm.test.common import assert_equal
from csm.common.permission_names import R, A
from csm.core.services.permissions import PermissionSet


def test_permissions_union(*args):
    lhs = PermissionSet({
        R.ALERT: {A.LIST, A.UPDATE},
        R.USER: {A.CREATE, A.DELETE, A.UPDATE},
        R.S3USER: {A.LIST}
    })
    rhs = PermissionSet({
        R.ALERT: {A.CREATE, A.LIST},
        R.USER: {A.LIST, A.CREATE, A.DELETE},
        R.STAT: {A.LIST}
    })

    calculated = lhs | rhs

    expected = Permissions({
        R.ALERT: {A.UPDATE, A.LIST, A.CREATE},
        R.USER: {A.UPDATE, A.CREATE, A.LIST, A.DELETE},
        R.S3USER: {A.LIST},
        R.STAT: {A.LIST}
    })

    assert_equal(calculated, expected)


def test_permissions_intersection(*args):
    lhs = PermissionSet({
        R.ALERT: {A.LIST, A.UPDATE},
        R.USER: {A.CREATE, A.DELETE, A.UPDATE},
        R.S3USER: {A.LIST}
    })
    rhs = PermissionSet({
        R.ALERT: {A.CREATE, A.LIST},
        R.USER: {A.LIST, A.CREATE, A.DELETE},
        R.STAT: {A.LIST}
    })

    calculated = lhs & rhs

    expected = PermissionSet({
        R.ALERT: {A.LIST},
        R.USER: {A.CREATE, A.DELETE}
    })

    assert_equal(calculated, expected)


def init(args):
    pass


test_list = [
    test_permissions_union,
    test_permissions_intersection,
]
