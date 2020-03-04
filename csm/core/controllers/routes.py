#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          routes.py
 Description:       adding route to web application

 Creation Date:     10/16/2019
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
# To add new route import from view file
from .view import CsmView
from .stats import StatsView
from .login import LoginView, LogoutView
from .onboarding import OnboardingStateView
from .system_config import SystemConfigListView
from .system_config import SystemConfigView
from .storage_capacity import StorageCapacityView
from .permissions import CurrentPermissionsView
from .firmware_update import FirmwarePackageUploadView, FirmwareUpdateView
from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
from csm.core.controllers.s3.iam_users import IamUserView,  IamUserListView
from csm.core.controllers.s3.buckets import S3BucketListView, S3BucketView, S3BucketPolicyView


class CsmRoutes():
    """
    Common class for adding routes
    """

    @staticmethod
    def add_routes(app):
        """
        Add routes to Web application
        """
        app.add_routes(CsmView._app_routes)

