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
from eos.utils.log import Log
from csm.core.blogic import const
from csm.common.conf import Conf
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.core.data.models.upgrade import UpdateStatusEntry
from csm.core.services.update_service import UpdateService

import os
import datetime


class FirmwareUpdateService(UpdateService):
    
    def __init__(self, provisioner, storage_path, update_repo):
        super().__init__(provisioner, update_repo)
        self._fw_storage_path = storage_path

    async def upload_package(self, package_ref, filename):
        """
        Service to upload and validate firmware package. Also returns last
        firmware ugrade status
        :param package_ref: FileRef object
        :param filename: str
        :return: dict
        """
        firmware_package_path = package_ref.save_file(self._fw_storage_path, filename, True)
        model = await self._update_repo.get_current_model(const.FIRMWARE_UPDATE_ID)
        if model and model.is_in_progress():
            raise InvalidRequest("You can't upload a new package while there is an ongoing update")

        model = UpdateStatusEntry.generate_new(const.FIRMWARE_UPDATE_ID)
        model.description = os.path.join(self._fw_storage_path, filename)
        model.details = ''
        model.mark_uploaded()
        await self._update_repo.save_model(model)
        return model.to_printable()
    
    async def start_update(self):
        software_update_model = await self._get_renewed_model(const.SOFTWARE_UPDATE_ID)

        if software_update_model and software_update_model.is_in_progress():
            raise InvalidRequest("Software update is already in progress. Please wait until it is done.")

        firmware_update_model = await self._get_renewed_model(const.FIRMWARE_UPDATE_ID)
        if not firmware_update_model:
            raise CsmInternalError("Internal DB is inconsistent. Please upload the package again")

        if firmware_update_model.is_in_progress():
            raise InvalidRequest("Firmware update is already in progress. Please wait until it is done.")

        firmware_update_model.provisioner_id = await self._provisioner.trigger_firmware_update(firmware_update_model.description)
        firmware_update_model.mark_started()
        await self._update_repo.save_model(firmware_update_model)
        return firmware_update_model.to_printable()
    
    async def check_for_package_availability(self):
        """
        Service to check package is available at configured path
        :return: dict
        """
        model = await self._get_renewed_model(const.FIRMWARE_UPDATE_ID)
        if not model:
            raise CsmError(desc="Internal DB is inconsistent. Please upload the package again")
        if not model.description or not os.path.exists(model.description):
            raise InvalidRequest(f"Firmware package {model.description} not found.")
        return model.to_printable()
 
    async def get_current_status(self):
        return await super()._get_current_status(const.FIRMWARE_UPDATE_ID)