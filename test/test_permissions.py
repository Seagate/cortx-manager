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
