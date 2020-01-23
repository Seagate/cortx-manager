from csm.core.services.roles_management import RolesManagementService
import unittest
import json


roles_dict = {
    'manage':{ 
          'permissions': {
               'alert': { 'list': True, 'update': True },
               'stat': { 'list': True, 'update': False }
          }
    },
    'monitor': {
          'permissions': {
              'alert': { 'list': True, 'update': False },
              'stat': { 'list': True, 'update': False }
          }
    }
}

t = unittest.TestCase()

def test_manage_roles(*args):
    rms = RolesManagementService(roles_dict)
    expected_permissions = {
        'permissions': {
            'alert': { 'list': True, 'update': True },
            'stat': { 'list': True, 'update': False }
        }
    }    
     
    actual_permissions = rms.get_permissions(['manage'])

    t.assertEqual(actual_permissions, expected_permissions)

def test_manage_roles_with_root(*args):
    rms = RolesManagementService(roles_dict)
    expected_permissions = {
        'permissions': {
            'alert': { 'list': True, 'update': True },
            'stat': { 'list': True, 'update': False }
        }
    }    
     
    actual_permissions = rms.get_permissions(['root', 'manage'])

    t.assertEqual(actual_permissions, expected_permissions)

def test_monitor_roles(*args):
    rms = RolesManagementService(roles_dict)
    expected_permissions = {
        'permissions': {
            'alert': { 'list': True, 'update': False },
            'stat': { 'list': True, 'update': False }
        }
    }    
     
    actual_permissions = rms.get_permissions(['monitor'])

    t.assertEqual(actual_permissions, expected_permissions)

def test_invalid_roles(*args):
    rms = RolesManagementService(roles_dict)
    with t.assertRaises(Exception) as context:
        rms.get_permissions(['nfs'])

def init(args):
    pass    
    
test_list = [
                test_manage_roles,
                test_monitor_roles,
                test_manage_roles_with_root,
                test_invalid_roles,
            ]

