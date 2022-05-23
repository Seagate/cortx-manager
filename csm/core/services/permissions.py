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

class PermissionSet:
    """Permission Set stored in a compact way as a dictionary."""

    def __init__(self, items: dict = {}):
        self._items = {
            resource: set(actions)
                for resource, actions in items.items()
                    if len(actions) > 0
        }

    def __str__(self) -> str:
        """String Representation Operator."""

        return f'{self.__class__.__name__}{self._items.__str__()}'

    def __eq__(self, other: 'PermissionSet') -> bool:
        """Equality Operator."""

        return self._items == other._items

    def __or__(self, other: 'PermissionSet') -> 'PermissionSet':
        """Union Operator."""

        result = PermissionSet()
        resources = set(self._items.keys()) | set(other._items.keys())
        for resource in resources:
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            actions = lhs_actions | rhs_actions
            if len(actions) > 0:
                result._items[resource] = actions
        return result

    def __and__(self, other: 'PermissionSet') -> 'PermissionSet':
        """Intersection Operator."""

        result = PermissionSet()
        resources = set(self._items.keys()) & set(other._items.keys())
        for resource in resources:
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            actions = lhs_actions & rhs_actions
            if len(actions) > 0:
                result._items[resource] = actions
        return result

    def __ior__(self, other: 'PermissionSet') -> 'PermissionSet':
        """In-place Union Operator."""

        for resource in other._items.keys():
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            actions = lhs_actions | rhs_actions
            if len(actions) > 0:
                self._items[resource] = actions
            else:
                self._items.pop(resource, None)
        return self

    def __iand__(self, other: 'PermissionSet') -> 'PermissionSet':
        """In-place Intersection Operator."""

        for resource in self._items.keys():
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            actions = lhs_actions & rhs_actions
            if len(actions) > 0:
                self._items[resource] = actions
            else:
                self._items.pop(resource, None)
        return self
