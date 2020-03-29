#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          firmware_update.py
 Description:       Service(s) for firmware update.

 Creation Date:     02/25/2020
 Author:            Udayan Yaragattikar


 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.common.services import ApplicationService
from csm.common.log import Log
from csm.core.blogic import const
from csm.common.conf import Conf
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.core.data.models.upgrade import UpdateStatusEntry

import os
import datetime


class FirmwareUpdateService(ApplicationService):
    """
    Service for firmware package upload
    """
    FIRMWARE_UPDATE_ID = 'firmware_update'
    def __init__(self, provisioner, fw_storage_path: str, firmware_repo):
        self._provisioner = provisioner
        self._fw_storage_path = fw_storage_path
        self._firmware_repo = firmware_repo


    @Log.trace_method(Log.DEBUG)
    async def _get_renewed_model(self) -> UpdateStatusEntry:
        """
        Fetch the most up-to-date information about the most recent firmware upgrade process.
        Queries the DB, then queries the Provisioner if needed.
        """
        model = await self._firmware_repo.get_current_model(self.FIRMWARE_UPDATE_ID)
        if model and model.is_in_progress():
            try:
                result = await self._provisioner.get_upgrade_status(model.provisioner_id)
                model.apply_status_update(result)
                await self._firmware_repo.save_model(model)
            except Exception as e:
                raise CsmInternalError(f'Failed to fetch the status of an ongoing upgrade process')

        return model

    @Log.trace_method(Log.INFO)
    async def get_current_status(self):
        """
        Fetch current state of firmware update process.
        Synchronizes it with the Provisioner service if necessary.

        Returns {} if there is no information (e.g. because CSM has never been updated)
        Otherwise returns a dictionary that describes the process
        """
        model = await self._get_renewed_model()
        if not model:
            return {}

        return model.to_printable()

    async def firmware_package_upload(self, package_ref, filename):
        """
        Service to upload and validate firmware package. Also returns last
        firmware ugrade status
        :param package_ref: FileRef object
        :param filename: str
        :return: dict
        """
        firmware_package_path = package_ref.save_file(self._fw_storage_path, filename, True)
        model = await self._firmware_repo.get_current_model(self.FIRMWARE_UPDATE_ID)
        if model and model.is_in_progress():
            raise InvalidRequest("You can't upload a new package while there is an ongoing upgrade")
        model = UpdateStatusEntry.generate_new(self.FIRMWARE_UPDATE_ID)
        model.version = datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")
        model.description = os.path.join(self._fw_storage_path, filename)
        model.mark_uploaded()
        await self._firmware_repo.save_model(model)
        return model.to_printable()

    async def trigger_firmware_upload(self):
        """
        Service to trigger firmware upgrade
        :return:
        """
        model = await self._get_renewed_model()
        if not model:
            raise CsmInternalError("Internal DB is iconsistent. Please upload the package again")
        if model.is_in_progress():
            raise InvalidRequest("Firmware upgrade is already in progress. Please wait until it is done.")

        model.provisioner_id = await self._provisioner.trigger_firmware_upload(model.description)
        model.mark_started()
        await self._firmware_repo.save_model(model)
        return model.to_printable()

    async def check_for_package_availability(self):
        """
        Service to check package is available at configured path
        :return: dict
        """
        model = await self._get_renewed_model()
        if not model:
            raise CsmError("Internal DB is inconsistent. Please upload the package again")
        if not model.description or not os.path.exists(model.description):
            raise InvalidRequest(f"Firmware package {model.description} not found.")
        return model.to_printable()
