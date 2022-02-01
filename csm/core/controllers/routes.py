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

# To add new route import from view file
from .view import CsmView
from .stats import StatsView
from .login import LoginView, LogoutView
from .onboarding import OnboardingStateView
from .system_config import SystemConfigListView
from .system_config import SystemConfigView
from .storage_capacity import StorageCapacityView
from .permissions import CurrentPermissionsView
from .hotfix_update import CsmHotfixUploadView
from .firmware_update import (FirmwarePackageUploadView, FirmwareUpdateView,
                              FirmwarePackageAvailibility)
from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
from csm.core.controllers.s3.access_keys import S3AccessKeysListView, S3AccessKeysView  # noqa: F401
from csm.core.controllers.s3.iam_users import IamUserView,  IamUserListView
from csm.core.controllers.s3.buckets import S3BucketListView, S3BucketView, S3BucketPolicyView
from csm.core.controllers.s3.server_info import S3ServerInfoView
from csm.core.controllers.security import (SecurityInstallView, SecurityStatusView,
                                           SecurityUploadView, SecurityDetailsView)
from csm.core.controllers.maintenance import MaintenanceView
from csm.core.controllers.version import ProductVersionView
from csm.core.controllers.health import ResourcesHealthView
from csm.core.controllers.cluster_management import ClusterOperationsView, ClusterStatusView
from csm.core.controllers.appliance_info import ApplianceInfoView
from csm.core.controllers.unsupported_features import UnsupportedFeaturesView
from csm.core.controllers.system_status import SystemStatusView, SystemStatusAllView
from csm.core.controllers.rgw.s3.users import UserListView


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
