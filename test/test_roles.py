import os
import json
from aiohttp import web
from unittest.mock import MagicMock

from csm.test.common import (
    Const,
    TestFailed,
    assert_equal,
    assert_raises,
    async_test,
    async_return,
    get_type_name
)
from csm.core.services.roles import RoleManager
from csm.core.services.permissions import PermissionSet

from csm.core.agent.api import CsmRestApi

from csm.core.controllers.alerts.alerts import (
    AlertsListView,
    AlertsView,
    AlertCommentsView
)
from csm.core.controllers.alerts.alerts_history import (
    AlertsHistoryListView,
    AlertsHistoryView
)
from csm.core.controllers.audit_log import (
    AuditLogShowView,
    AuditLogDownloadView
)
from csm.core.controllers.firmware_update import (
    FirmwarePackageUploadView,
    FirmwareUpdateView,
    FirmwareUpdateStatusView,
    FirmwarePackageAvailibility
)
from csm.core.controllers.health import (
    HealthSummaryView,
    HealthView,
    NodeHealthView
)
from csm.core.controllers.login import LoginView, LogoutView
from csm.core.controllers.maintenance import MaintenanceView
from csm.core.controllers.onboarding import OnboardingStateView
from csm.core.controllers.permissions import (
    CurrentPermissionsView,
    UserPermissionsView
)
from csm.core.controllers.stats import StatsView, StatsPanelListView
from csm.core.controllers.storage_capacity import StorageCapacityView
from csm.core.controllers.system_config import (
    SystemConfigListView,
    SystemConfigView,
    TestEmailView,
    OnboardingLicenseView
)
from csm.core.controllers.users import (
    CsmUsersListView,
    CsmUsersView,
    AdminUserView
)
from csm.core.controllers.s3.accounts import (
    S3AccountsListView,
    S3AccountsView
)
from csm.core.controllers.s3.buckets import (
    S3BucketListView,
    S3BucketView,
    S3BucketPolicyView
)
from csm.core.controllers.s3.iam_users import IamUserListView, IamUserView
from csm.core.controllers.security import (SecurityInstallView, SecurityStatusView,
                                           SecurityUploadView)


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


CSM_BASE_DIRS = [
    os.path.join(os.path.dirname(__file__), '..'),
    Const.CSM_PATH,
]

def open_schema_file(filename, mode='r'):
    """ Helper function for opening file either from the directory
        with the source code or from global installation path """

    for basepath in CSM_BASE_DIRS:
        fullpath = os.path.join(basepath, 'schema', filename)
        try:
            return open(fullpath, mode)
        except OSError:
            pass
    raise TestFailed(f'Can\'t open file {filename}')


async def check_rest_ep_permissions(role_manager, handler, method, roles, must_fail):
    """ Helper function for testing one REST API endpoint using a list of roles """

    async def null_handler(request):
        return None

    request = MagicMock()
    request.method = method
    request.match_info.handler = handler
    request.app.router.resolve.return_value = async_return(request.match_info)
    request.session.permissions = PermissionSet()

    if roles:
        request.session.permissions = \
            await role_manager.calc_effective_permissions(*roles)

    try:
        if must_fail:
            with assert_raises(web.HTTPForbidden):
                await CsmRestApi.permission_middleware(request, null_handler)
        else:
            await CsmRestApi.permission_middleware(request, null_handler)
    except Exception as e:
        handler_name = get_type_name(handler)
        raise TestFailed(f'{handler_name}: {method} as {roles} -- {e}')


class Method:
    """ HTTP method names """

    GET = 'GET'
    DELETE = 'DELETE'
    PATCH = 'PATCH'
    POST = 'POST'
    PUT = 'PUT'


class User:
    """ Typical users with predefined roles """

    Anon = []
    CsmAdmin = ['root', 'manage']
    CsmUser = ['monitor']
    S3Account = ['s3']


class Access:
    """ Access verdict constants """

    OK = True
    FAIL = False


async def test_rest_ep_permissions(*args):
    """ Check an accessibiliy of all REST API endpoints using predefined roles """

    with open_schema_file('roles.json') as f:
        predefined_roles = json.load(f)

    role_manager = RoleManager(predefined_roles)

    rest_ep_cases = [
        (AlertsListView           , Method.GET   , User.Anon     , Access.FAIL),
        (AlertsListView           , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AlertsListView           , Method.GET   , User.CsmUser  , Access.OK  ),
        (AlertsListView           , Method.GET   , User.S3Account, Access.FAIL),

        (AlertsListView           , Method.PATCH , User.Anon     , Access.FAIL),
        (AlertsListView           , Method.PATCH , User.CsmAdmin , Access.OK  ),
        (AlertsListView           , Method.PATCH , User.CsmUser  , Access.FAIL),
        (AlertsListView           , Method.PATCH , User.S3Account, Access.FAIL),

        (AlertsView               , Method.GET   , User.Anon     , Access.FAIL),
        (AlertsView               , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AlertsView               , Method.GET   , User.CsmUser  , Access.OK  ),
        (AlertsView               , Method.GET   , User.S3Account, Access.FAIL),

        (AlertsView               , Method.PATCH , User.Anon     , Access.FAIL),
        (AlertsView               , Method.PATCH , User.CsmAdmin , Access.OK  ),
        (AlertsView               , Method.PATCH , User.CsmUser  , Access.FAIL),
        (AlertsView               , Method.PATCH , User.S3Account, Access.FAIL),

        (AlertCommentsView        , Method.GET   , User.Anon     , Access.FAIL),
        (AlertCommentsView        , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AlertCommentsView        , Method.GET   , User.CsmUser  , Access.OK  ),
        (AlertCommentsView        , Method.GET   , User.S3Account, Access.FAIL),

        (AlertCommentsView        , Method.POST  , User.Anon     , Access.FAIL),
        (AlertCommentsView        , Method.POST  , User.CsmAdmin , Access.OK  ),
        (AlertCommentsView        , Method.POST  , User.CsmUser  , Access.FAIL),
        (AlertCommentsView        , Method.POST  , User.S3Account, Access.FAIL),

        (AlertsHistoryListView    , Method.GET   , User.Anon     , Access.FAIL),
        (AlertsHistoryListView    , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AlertsHistoryListView    , Method.GET   , User.CsmUser  , Access.OK  ),
        (AlertsHistoryListView    , Method.GET   , User.S3Account, Access.FAIL),

        (AlertsHistoryView        , Method.GET   , User.Anon     , Access.FAIL),
        (AlertsHistoryView        , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AlertsHistoryView        , Method.GET   , User.CsmUser  , Access.OK  ),
        (AlertsHistoryView        , Method.GET   , User.S3Account, Access.FAIL),

        (AuditLogShowView         , Method.GET   , User.Anon     , Access.FAIL),
        (AuditLogShowView         , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AuditLogShowView         , Method.GET   , User.CsmUser  , Access.OK  ),
        (AuditLogShowView         , Method.GET   , User.S3Account, Access.FAIL),

        (AuditLogDownloadView     , Method.GET   , User.Anon     , Access.FAIL),
        (AuditLogDownloadView     , Method.GET   , User.CsmAdmin , Access.OK  ),
        (AuditLogDownloadView     , Method.GET   , User.CsmUser  , Access.OK  ),
        (AuditLogDownloadView     , Method.GET   , User.S3Account, Access.FAIL),

        (FirmwarePackageUploadView, Method.POST  , User.Anon     , Access.FAIL),
        (FirmwarePackageUploadView, Method.POST  , User.CsmAdmin , Access.OK  ),
        (FirmwarePackageUploadView, Method.POST  , User.CsmUser  , Access.FAIL),
        (FirmwarePackageUploadView, Method.POST  , User.S3Account, Access.FAIL),

        (FirmwareUpdateView       , Method.POST  , User.Anon     , Access.FAIL),
        (FirmwareUpdateView       , Method.POST  , User.CsmAdmin , Access.OK  ),
        (FirmwareUpdateView       , Method.POST  , User.CsmUser  , Access.FAIL),
        (FirmwareUpdateView       , Method.POST  , User.S3Account, Access.FAIL),

        (FirmwareUpdateStatusView , Method.GET   , User.Anon     , Access.FAIL),
        (FirmwareUpdateStatusView , Method.GET   , User.CsmAdmin , Access.OK  ),
        (FirmwareUpdateStatusView , Method.GET   , User.CsmUser  , Access.FAIL),
        (FirmwareUpdateStatusView , Method.GET   , User.S3Account, Access.FAIL),

        (FirmwarePackageAvailibility, Method.GET , User.Anon     , Access.FAIL),
        (FirmwarePackageAvailibility, Method.GET , User.CsmAdmin , Access.OK  ),
        (FirmwarePackageAvailibility, Method.GET , User.CsmUser  , Access.FAIL),
        (FirmwarePackageAvailibility, Method.GET , User.S3Account, Access.FAIL),

        (HealthSummaryView        , Method.GET   , User.Anon     , Access.FAIL),
        (HealthSummaryView        , Method.GET   , User.CsmAdmin , Access.OK  ),
        (HealthSummaryView        , Method.GET   , User.CsmUser  , Access.OK  ),
        (HealthSummaryView        , Method.GET   , User.S3Account, Access.FAIL),

        (HealthView               , Method.GET   , User.Anon     , Access.FAIL),
        (HealthView               , Method.GET   , User.CsmAdmin , Access.OK  ),
        (HealthView               , Method.GET   , User.CsmUser  , Access.OK  ),
        (HealthView               , Method.GET   , User.S3Account, Access.FAIL),

        (NodeHealthView           , Method.GET   , User.Anon     , Access.FAIL),
        (NodeHealthView           , Method.GET   , User.CsmAdmin , Access.OK  ),
        (NodeHealthView           , Method.GET   , User.CsmUser  , Access.OK  ),
        (NodeHealthView           , Method.GET   , User.S3Account, Access.FAIL),

        (LoginView                , Method.POST  , User.Anon     , Access.OK  ),
        (LoginView                , Method.POST  , User.CsmAdmin , Access.OK  ),
        (LoginView                , Method.POST  , User.CsmUser  , Access.OK  ),
        (LoginView                , Method.POST  , User.S3Account, Access.OK  ),

        (LogoutView               , Method.POST  , User.Anon     , Access.OK  ),
        (LogoutView               , Method.POST  , User.CsmAdmin , Access.OK  ),
        (LogoutView               , Method.POST  , User.CsmUser  , Access.OK  ),
        (LogoutView               , Method.POST  , User.S3Account, Access.OK  ),

        (MaintenanceView          , Method.GET   , User.Anon     , Access.FAIL),
        (MaintenanceView          , Method.GET   , User.CsmAdmin , Access.OK  ),
        (MaintenanceView          , Method.GET   , User.CsmUser  , Access.FAIL),
        (MaintenanceView          , Method.GET   , User.S3Account, Access.FAIL),

        (OnboardingStateView      , Method.GET   , User.Anon     , Access.OK  ),
        (OnboardingStateView      , Method.GET   , User.CsmAdmin , Access.OK  ),
        (OnboardingStateView      , Method.GET   , User.CsmUser  , Access.OK  ),
        (OnboardingStateView      , Method.GET   , User.S3Account, Access.OK  ),

        (OnboardingStateView      , Method.PATCH , User.Anon     , Access.FAIL),
        (OnboardingStateView      , Method.PATCH , User.CsmAdmin , Access.OK  ),
        (OnboardingStateView      , Method.PATCH , User.CsmUser  , Access.FAIL),
        (OnboardingStateView      , Method.PATCH , User.S3Account, Access.FAIL),

        (CurrentPermissionsView   , Method.GET   , User.Anon     , Access.FAIL),
        (CurrentPermissionsView   , Method.GET   , User.CsmAdmin , Access.OK  ),
        (CurrentPermissionsView   , Method.GET   , User.CsmUser  , Access.OK  ),
        (CurrentPermissionsView   , Method.GET   , User.S3Account, Access.OK  ),

        (UserPermissionsView      , Method.GET   , User.Anon     , Access.FAIL),
        (UserPermissionsView      , Method.GET   , User.CsmAdmin , Access.OK  ),
        (UserPermissionsView      , Method.GET   , User.CsmUser  , Access.OK  ),
        (UserPermissionsView      , Method.GET   , User.S3Account, Access.OK  ),

        (StatsView                , Method.GET   , User.Anon     , Access.FAIL),
        (StatsView                , Method.GET   , User.CsmAdmin , Access.OK  ),
        (StatsView                , Method.GET   , User.CsmUser  , Access.OK  ),
        (StatsView                , Method.GET   , User.S3Account, Access.FAIL),

        (StatsPanelListView       , Method.GET   , User.Anon     , Access.FAIL),
        (StatsPanelListView       , Method.GET   , User.CsmAdmin , Access.OK  ),
        (StatsPanelListView       , Method.GET   , User.CsmUser  , Access.OK  ),
        (StatsPanelListView       , Method.GET   , User.S3Account, Access.FAIL),

        (StorageCapacityView      , Method.GET   , User.Anon     , Access.FAIL),
        (StorageCapacityView      , Method.GET   , User.CsmAdmin , Access.OK  ),
        (StorageCapacityView      , Method.GET   , User.CsmUser  , Access.OK  ),
        (StorageCapacityView      , Method.GET   , User.S3Account, Access.FAIL),

        (SystemConfigListView     , Method.GET   , User.Anon     , Access.FAIL),
        (SystemConfigListView     , Method.GET   , User.CsmAdmin , Access.OK  ),
        (SystemConfigListView     , Method.GET   , User.CsmUser  , Access.FAIL),
        (SystemConfigListView     , Method.GET   , User.S3Account, Access.FAIL),

        (SystemConfigListView     , Method.POST  , User.Anon     , Access.FAIL),
        (SystemConfigListView     , Method.POST  , User.CsmAdmin , Access.OK  ),
        (SystemConfigListView     , Method.POST  , User.CsmUser  , Access.FAIL),
        (SystemConfigListView     , Method.POST  , User.S3Account, Access.FAIL),

        (SystemConfigView         , Method.GET   , User.Anon     , Access.FAIL),
        (SystemConfigView         , Method.GET   , User.CsmAdmin , Access.OK  ),
        (SystemConfigView         , Method.GET   , User.CsmUser  , Access.FAIL),
        (SystemConfigView         , Method.GET   , User.S3Account, Access.FAIL),

        (SystemConfigView         , Method.PUT   , User.Anon     , Access.FAIL),
        (SystemConfigView         , Method.PUT   , User.CsmAdmin , Access.OK  ),
        (SystemConfigView         , Method.PUT   , User.CsmUser  , Access.FAIL),
        (SystemConfigView         , Method.PUT   , User.S3Account, Access.FAIL),

        (TestEmailView            , Method.POST  , User.Anon     , Access.FAIL),
        (TestEmailView            , Method.POST  , User.CsmAdmin , Access.OK  ),
        (TestEmailView            , Method.POST  , User.CsmUser  , Access.FAIL),
        (TestEmailView            , Method.POST  , User.S3Account, Access.FAIL),

        (OnboardingLicenseView    , Method.POST  , User.Anon     , Access.FAIL),
        (OnboardingLicenseView    , Method.POST  , User.CsmAdmin , Access.OK  ),
        (OnboardingLicenseView    , Method.POST  , User.CsmUser  , Access.FAIL),
        (OnboardingLicenseView    , Method.POST  , User.S3Account, Access.FAIL),

        (CsmUsersListView         , Method.GET   , User.Anon     , Access.FAIL),
        (CsmUsersListView         , Method.GET   , User.CsmAdmin , Access.OK  ),
        (CsmUsersListView         , Method.GET   , User.CsmUser  , Access.OK  ),
        (CsmUsersListView         , Method.GET   , User.S3Account, Access.FAIL),
        (CsmUsersListView         , Method.POST  , User.Anon     , Access.FAIL),
        (CsmUsersListView         , Method.POST  , User.CsmAdmin , Access.OK  ),
        (CsmUsersListView         , Method.POST  , User.CsmUser  , Access.FAIL),
        (CsmUsersListView         , Method.POST  , User.S3Account, Access.FAIL),

        (CsmUsersView             , Method.GET   , User.Anon     , Access.FAIL),
        (CsmUsersView             , Method.GET   , User.CsmAdmin , Access.OK  ),
        (CsmUsersView             , Method.GET   , User.CsmUser  , Access.OK  ),
        (CsmUsersView             , Method.GET   , User.S3Account, Access.FAIL),
        (CsmUsersView             , Method.PATCH , User.Anon     , Access.FAIL),
        (CsmUsersView             , Method.PATCH , User.CsmAdmin , Access.OK  ),
        (CsmUsersView             , Method.PATCH , User.CsmUser  , Access.FAIL),
        (CsmUsersView             , Method.PATCH , User.S3Account, Access.FAIL),
        (CsmUsersView             , Method.DELETE, User.Anon     , Access.FAIL),
        (CsmUsersView             , Method.DELETE, User.CsmAdmin , Access.OK  ),
        (CsmUsersView             , Method.DELETE, User.CsmUser  , Access.FAIL),
        (CsmUsersView             , Method.DELETE, User.S3Account, Access.FAIL),

        (AdminUserView            , Method.POST  , User.Anon     , Access.OK  ),
        (AdminUserView            , Method.POST  , User.CsmAdmin , Access.OK  ),
        (AdminUserView            , Method.POST  , User.CsmUser  , Access.OK  ),
        (AdminUserView            , Method.POST  , User.S3Account, Access.OK  ),

        (S3AccountsListView       , Method.GET   , User.Anon     , Access.FAIL),
        (S3AccountsListView       , Method.GET   , User.CsmAdmin , Access.OK  ),
        (S3AccountsListView       , Method.GET   , User.CsmUser  , Access.OK  ),
        (S3AccountsListView       , Method.GET   , User.S3Account, Access.OK  ),

        (S3AccountsListView       , Method.POST  , User.Anon     , Access.FAIL),
        (S3AccountsListView       , Method.POST  , User.CsmAdmin , Access.OK  ),
        (S3AccountsListView       , Method.POST  , User.CsmUser  , Access.FAIL),
        (S3AccountsListView       , Method.POST  , User.S3Account, Access.FAIL),

        (S3AccountsView           , Method.DELETE, User.Anon     , Access.FAIL),
        (S3AccountsView           , Method.DELETE, User.CsmAdmin , Access.FAIL),
        (S3AccountsView           , Method.DELETE, User.CsmUser  , Access.FAIL),
        (S3AccountsView           , Method.DELETE, User.S3Account, Access.OK  ),

        (S3AccountsView           , Method.PATCH , User.Anon     , Access.FAIL),
        (S3AccountsView           , Method.PATCH , User.CsmAdmin , Access.FAIL),
        (S3AccountsView           , Method.PATCH , User.CsmUser  , Access.FAIL),
        (S3AccountsView           , Method.PATCH , User.S3Account, Access.OK  ),

        (S3BucketListView         , Method.GET   , User.Anon     , Access.FAIL),
        (S3BucketListView         , Method.GET   , User.CsmAdmin , Access.FAIL),
        (S3BucketListView         , Method.GET   , User.CsmUser  , Access.FAIL),
        (S3BucketListView         , Method.GET   , User.S3Account, Access.OK  ),

        (S3BucketListView         , Method.POST  , User.Anon     , Access.FAIL),
        (S3BucketListView         , Method.POST  , User.CsmAdmin , Access.FAIL),
        (S3BucketListView         , Method.POST  , User.CsmUser  , Access.FAIL),
        (S3BucketListView         , Method.POST  , User.S3Account, Access.OK  ),

        (S3BucketView             , Method.DELETE, User.Anon     , Access.FAIL),
        (S3BucketView             , Method.DELETE, User.CsmAdmin , Access.FAIL),
        (S3BucketView             , Method.DELETE, User.CsmUser  , Access.FAIL),
        (S3BucketView             , Method.DELETE, User.S3Account, Access.OK  ),

        (S3BucketPolicyView       , Method.GET   , User.Anon     , Access.FAIL),
        (S3BucketPolicyView       , Method.GET   , User.CsmAdmin , Access.FAIL),
        (S3BucketPolicyView       , Method.GET   , User.CsmUser  , Access.FAIL),
        (S3BucketPolicyView       , Method.GET   , User.S3Account, Access.OK  ),

        (S3BucketPolicyView       , Method.PUT   , User.Anon     , Access.FAIL),
        (S3BucketPolicyView       , Method.PUT   , User.CsmAdmin , Access.FAIL),
        (S3BucketPolicyView       , Method.PUT   , User.CsmUser  , Access.FAIL),
        (S3BucketPolicyView       , Method.PUT   , User.S3Account, Access.OK  ),

        (S3BucketPolicyView       , Method.DELETE, User.Anon     , Access.FAIL),
        (S3BucketPolicyView       , Method.DELETE, User.CsmAdmin , Access.FAIL),
        (S3BucketPolicyView       , Method.DELETE, User.CsmUser  , Access.FAIL),
        (S3BucketPolicyView       , Method.DELETE, User.S3Account, Access.OK  ),

        (IamUserListView          , Method.GET   , User.Anon     , Access.FAIL),
        (IamUserListView          , Method.GET   , User.CsmAdmin , Access.FAIL),
        (IamUserListView          , Method.GET   , User.CsmUser  , Access.FAIL),
        (IamUserListView          , Method.GET   , User.S3Account, Access.OK  ),

        (IamUserListView          , Method.POST  , User.Anon     , Access.FAIL),
        (IamUserListView          , Method.POST  , User.CsmAdmin , Access.FAIL),
        (IamUserListView          , Method.POST  , User.CsmUser  , Access.FAIL),
        (IamUserListView          , Method.POST  , User.S3Account, Access.OK  ),

        (IamUserView              , Method.DELETE, User.Anon     , Access.FAIL),
        (IamUserView              , Method.DELETE, User.CsmAdmin , Access.FAIL),
        (IamUserView              , Method.DELETE, User.CsmUser  , Access.FAIL),
        (IamUserView              , Method.DELETE, User.S3Account, Access.OK  ),

        (SecurityUploadView       , Method.POST, User.Anon     , Access.FAIL),
        (SecurityUploadView       , Method.POST, User.CsmAdmin , Access.OK),
        (SecurityUploadView       , Method.POST, User.CsmUser  , Access.FAIL),
        (SecurityUploadView       , Method.POST, User.S3Account, Access.FAIL),

        (SecurityStatusView       , Method.GET, User.Anon     , Access.FAIL),
        (SecurityStatusView       , Method.GET, User.CsmAdmin , Access.OK),
        (SecurityStatusView       , Method.GET, User.CsmUser  , Access.FAIL),
        (SecurityStatusView       , Method.GET, User.S3Account, Access.FAIL),

        (SecurityInstallView       , Method.POST, User.Anon     , Access.FAIL),
        (SecurityInstallView       , Method.POST, User.CsmAdmin , Access.OK),
        (SecurityInstallView       , Method.POST, User.CsmUser  , Access.FAIL),
        (SecurityInstallView       , Method.POST, User.S3Account, Access.FAIL),
    ]

    for handler, method, roles, access in rest_ep_cases:
        await check_rest_ep_permissions(role_manager, handler,
                                        method, roles, not access)


def init(args):
    pass


test_list = [
    async_test(test_manage_roles),
    async_test(test_monitor_roles),
    async_test(test_manage_roles_with_root),
    async_test(test_invalid_roles),
    async_test(test_rest_ep_permissions),
]
