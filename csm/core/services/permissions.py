#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          permissions.py
 Description:       Implementation of permission set.
                    Definition of resource and action names for permissions.

 Creation Date:     01/16/2020
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

class R:
    ''' Resource Names '''

    ALERT = 'alert'
    USER = 'user'
    STAT = 'stat'
    S3ACCOUNT = 's3account'
    S3USER = 's3user'


class A:
    ''' Action Names '''

    LIST = 'list'
    CREATE = 'create'
    DELETE = 'delete'
    UPDATE = 'update'


class Permissions:
    ''' Permission Set stored in a compact way as a dictionary '''

    def __init__(self, items: dict = {}):
        self._items = {
            resource: set(actions)
                for resource, actions in items.items()
        }

    def __str__(self) -> str:
        ''' String Representation Operator '''

        return self._items.__str__()

    def __eq__(self, other: 'Permissions') -> bool:
        ''' Equality Operator '''

        return self._items == other._items

    def __or__(self, other: 'Permissions') -> 'Permissions':
        ''' Union Operator '''

        result = Permissions()
        resources = set(self._items.keys()) | set(other._items.keys())
        for resource in resources:
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            result._items[resource] = lhs_actions | rhs_actions
        return result

    def __and__(self, other: 'Permissions') -> 'Permissions':
        ''' Intersection Operator '''

        result = Permissions()
        resources = set(self._items.keys()) & set(other._items.keys())
        for resource in resources:
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            result._items[resource] = lhs_actions & rhs_actions
        return result

    def __ior__(self, other: 'Permissions') -> 'Permissions':
        ''' In-place Union Operator '''

        for resource in other._items.keys():
            lhs_actions = self._items.get(resource, set())
            rhs_actions = other._items.get(resource, set())
            self._items[resource] = lhs_actions | rhs_actions
        return self

    def __iand__(self, other: 'Permissions') -> 'Permissions':
        ''' In-place Intersection Operator '''

        for resource in self._items.keys():
            if resource in other._items.keys():
                lhs_actions = self._items.get(resource, set())
                rhs_actions = other._items.get(resource, set())
                self._items[resource] = lhs_actions & rhs_actions
            else:
                self._items.pop(resource)
        return self
