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

import datetime
from enum import Enum
from schematics.types import StringType, DateTimeType
from csm.core.blogic.models.base import CsmModel
from cortx.utils.log import Log


class PackageInformation:
    """
    Model that is used by Provisioner plugin to communiate the package information
    """
    # TODO: add more files when there is more information about it
    version: str
    description: str


class ProvisionerCommandStatus(Enum):
    InProgress = 'in_progress'
    Success = 'success'
    Failure = 'failure'
    NotFound = 'not_found'
    Unknown = 'unknown'


class ProvisionerStatusResponse:
    """
    Model that is used by Provisioner plugin to communitate the result of status polling
    """
    status: ProvisionerCommandStatus
    details: str

    def __init__(self, status, details=''):
        self.status = status
        self.details = details


class UpdateStatus(Enum):
    Uploaded = 'uploaded'
    InProgress = 'in_progress'
    Success = 'success'
    Failure = 'fail'

    def __str__(self):
        return str(self.value)


class UpdateStatusEntry(CsmModel):
    """
    Model that is used to persist the current software upgrade status
    """
    _id = "update_type"
    update_type = StringType()  # Will serve as a primary key
    provisioner_id = StringType()
    status = StringType()
    version = StringType()
    description = StringType()
    details = StringType()
    updated_at = DateTimeType()
    uploaded_at = DateTimeType()
    started_at = DateTimeType()
    file_path = StringType()

    @classmethod
    def generate_new(cls, update_type):
        if not update_type:
            raise Exception("Update_type field must not be empty!")

        model = UpdateStatusEntry()
        model.update_type = update_type
        model.provisioner_id = None
        model.status = None
        model.description = ""
        model.details = ""
        model.version = None
        model.updated_at = datetime.datetime.now()
        model.uploaded_at = None
        model.started_at = None
        model.file_path = ""

        return model

    def is_in_progress(self) -> bool:
        return self.status == str(UpdateStatus.InProgress)

    def is_uploaded(self) -> bool:
        return self.status == str(UpdateStatus.Uploaded)

    def is_successful(self) -> bool:
        return self.status == str(UpdateStatus.Success)

    def mark_uploaded(self):
        self.uploaded_at = datetime.datetime.now()
        self.status = str(UpdateStatus.Uploaded)
        Log.info("Marking status for update as 'UPLOADED'.")

    def mark_started(self):
        self.started_at = datetime.datetime.now()
        self.status = str(UpdateStatus.InProgress)
        Log.info("Marking status for update as 'UPDATE STARTED'.")

    def apply_status_update(self, update: ProvisionerStatusResponse):
        Log.info(f"Updating status to {update.status}")
        if update.status in [ProvisionerCommandStatus.NotFound, ProvisionerCommandStatus.Failure]:
            self.status = str(UpdateStatus.Failure)
            self.details = update.details

        if update.status == ProvisionerCommandStatus.Success:
            self.status = str(UpdateStatus.Success)
            self.details = update.details

    def to_printable(self) -> dict:
        response = {
            "status": self.status,
            "version": self.version,
            "description": self.description,
            "details": self.details,
            "uploaded_at": None,
            "started_at": None,
            "updated_at": None,
            "file_path": self.file_path
        }

        if self.updated_at:
            response["updated_at"] = self.updated_at.isoformat()

        if self.uploaded_at:
            response["uploaded_at"] = self.uploaded_at.isoformat()

        if self.started_at:
            response["started_at"] = self.started_at.isoformat()

        return response