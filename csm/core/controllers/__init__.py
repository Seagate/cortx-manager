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

from .routes import CsmRoutes
from .users import CsmUsersListView, CsmUsersView
from .s3.iam_users import IamUserListView, IamUserView
from .s3.accounts import S3AccountsListView, S3AccountsView
from .alerts.alerts import AlertsView, AlertsListView
from .alerts.alerts_history import AlertsHistoryListView, AlertsHistoryView
from .health import ResourcesHealthView
from .cluster_management import ClusterOperationsView
from .audit_log import AuditLogShowView, AuditLogDownloadView
from .maintenance import MaintenanceView
from .rgw.s3.users import S3IAMUserListView, AccessKeyListView
# from .file_transfer import CsmFileView
from .usl import (DeviceRegistrationView, RegistrationTokenView, DeviceView, DeviceVolumesListView,
                  DeviceVolumeMountView, DeviceVolumeUnmountView, UdsEventsView, SystemView,
                  SystemCertificatesView,  SystemCertificatesByTypeView, NetworkInterfacesView)
