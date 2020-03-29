"""
 ****************************************************************************
 Filename:          upgrade.py
 Description:       Contains upgrade-related models

 Creation Date:     03/12/2020
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import uuid
import datetime
from enum import Enum
from schematics.types import IntType, StringType, DateType, ListType, DateTimeType
from csm.core.blogic.models import CsmModel


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

        return model

    def is_in_progress(self) -> bool:
        return self.status == str(UpdateStatus.InProgress)

    def is_uploaded(self) -> bool:
        return self.status == str(UpdateStatus.Uploaded)

    def mark_uploaded(self):
        self.uploaded_at = datetime.datetime.now()
        self.status = str(UpdateStatus.Uploaded)

    def mark_started(self):
        self.started_at = datetime.datetime.now()
        self.status = str(UpdateStatus.InProgress)

    def apply_status_update(self, update: ProvisionerStatusResponse):
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
            "updated_at": None
        }

        if self.updated_at:
            response["updated_at"] = self.updated_at.isoformat()

        if self.uploaded_at:
            response["uploaded_at"] = self.uploaded_at.isoformat()

        if self.started_at:
            response["started_at"] = self.started_at.isoformat()

        return response