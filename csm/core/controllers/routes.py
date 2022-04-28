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
from .storage_capacity import (CapacityStatusView, CapacityManagementView)
from .permissions import CurrentPermissionsView
from .users import CsmUsersListView, CsmUsersView
from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
from csm.core.controllers.health import ResourcesHealthView
from csm.core.controllers.cluster_management import ClusterOperationsView, ClusterStatusView, ClusterAvailabilityView
from csm.core.controllers.unsupported_features import UnsupportedFeaturesView
from csm.core.controllers.system_status import SystemStatusView, SystemStatusAllView
from csm.core.controllers.rgw.s3.users import (S3IAMUserListView, S3IAMUserView,
                                               S3IAMUserKeyView, S3IAMUserCapsView, S3IAMUserQuotaView)
from csm.core.controllers.rgw.s3.bucket import S3BucketView


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
