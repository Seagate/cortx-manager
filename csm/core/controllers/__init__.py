#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          __init__.py
 Description:       Module for exposing controllers as a single package

 Creation Date:     09/10/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from .routes import CsmRoutes
from .users import CsmUsersListView, CsmUsersView
from .s3.iam_users import IamUserListView, IamUserView
from .s3.accounts import S3AccountsListView, S3AccountsView
from .alerts.alerts import AlertsView, AlertsListView
from .alerts.alerts_history import AlertsHistoryListView, AlertsHistoryView
from .health import HealthView
from .audit_log import AuditLogShowView, AuditLogDownloadView
from .maintenance import MaintenanceView
from .node_replacement import ReplaceNodeView
# from .file_transfer import CsmFileView
from .usl import (DeviceRegistrationView, RegistrationTokenView, DeviceView, DeviceVolumesListView,
                  DeviceVolumeMountView, DeviceVolumeUnmountView, UdsEventsView, SystemView,
                  SystemCertificatesView,  SystemCertificatesByTypeView, NetworkInterfacesView)
