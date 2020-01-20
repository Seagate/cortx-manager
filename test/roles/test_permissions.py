import json
import unittest
from csm.core.services.permissions import Permissions, A, R


t = unittest.TestCase()


def test_permissions_union(*args):
    lhs = Permissions({
        R.ALERT: {A.LIST, A.UPDATE},
        R.USER: {A.CREATE, A.DELETE, A.UPDATE},
        R.S3USER: {A.LIST}
    })
    rhs = Permissions({
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

    t.assertEqual(calculated, expected)


def test_permissions_intersection(*args):
    lhs = Permissions({
        R.ALERT: {A.LIST, A.UPDATE},
        R.USER: {A.CREATE, A.DELETE, A.UPDATE},
        R.S3USER: {A.LIST}
    })
    rhs = Permissions({
        R.ALERT: {A.CREATE, A.LIST},
        R.USER: {A.LIST, A.CREATE, A.DELETE},
        R.STAT: {A.LIST}
    })

    calculated = lhs & rhs

    expected = Permissions({
        R.ALERT: {A.LIST},
        R.USER: {A.CREATE, A.DELETE}
    })

    t.assertEqual(calculated, expected)


def init(args):
    pass


test_list = [
    test_permissions_union,
    test_permissions_intersection,
]
