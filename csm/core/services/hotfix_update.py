#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          hotfix_update.py
 Description:       Services for update functionality

 Creation Date:     02/20/2020
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import datetime
import os
from marshmallow import Schema, fields
from csm.core.blogic import const
from csm.common.conf import Conf
from eos.utils.log import Log
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.common.services import Service, ApplicationService
from csm.core.data.models.upgrade import PackageInformation, UpdateStatusEntry
from csm.core.repositories.update_status import UpdateStatusRepository
from csm.core.services.update_service import UpdateService

   
class HotfixApplicationService(UpdateService):
    
    def __init__(self, storage_path, provisioner, update_repo):
        super().__init__(provisioner, update_repo)
        self._sw_file = os.path.join(storage_path, 'hotfix_fw_candidate.iso')
    
    @Log.trace_method(Log.INFO)
    async def upload_package(self, file_ref):
        """
        Upload and validate a hotfix update firmware package
        :param file_ref: An instance of FileRef class that represents a new update package
        :returns: An instance of PackageInformation
        """
        try:
            info = await self._provisioner.validate_hotfix_package(file_ref.get_file_path())
        except CsmError:
            raise InvalidRequest('You have uploaded an invalid hotfix firmware package')

        model = await self._get_renewed_model(const.SOFTWARE_UPDATE_ID)
        if model and model.is_in_progress():
            raise InvalidRequest("You can't upload a new package while there is an ongoing update")

        model = UpdateStatusEntry.generate_new(const.SOFTWARE_UPDATE_ID)
        model.version = info.version
        model.description = info.description
        model.mark_uploaded()
        await self._update_repo.save_model(model)

        try:
            file_ref.save_file(os.path.dirname(self._sw_file),
                os.path.basename(self._sw_file), True)
        except Exception as e:
            raise CsmInternalError(f'Failed to save the package: {e}')

        return {
            "version": info.version,
            "description": info.description
        }

    @Log.trace_method(Log.INFO)
    async def start_update(self):
        """
        Kicks off the hotfix application process
        :returns: Nothing
        """
        firmware_update_model = await self._get_renewed_model(const.FIRMWARE_UPDATE_ID)
        if firmware_update_model and firmware_update_model.is_in_progress():
            raise InvalidRequest("Firmware update is already in progress. Please wait until it is done.")

        software_update_model = await self._get_renewed_model(const.SOFTWARE_UPDATE_ID)

        if software_update_model and software_update_model.is_in_progress():
            raise InvalidRequest("Software update is already in progress. Please wait until it is done.")

        if not software_update_model.is_uploaded() or not os.path.exists(self._sw_file):
            raise InvalidRequest("You must upload an image before starting the software update.")

        software_update_model.provisioner_id = await self._provisioner.trigger_software_update(self._sw_file)
        software_update_model.mark_started()
        await self._update_repo.save_model(software_update_model)
        return {
            "message": "Software update has succesfully started"
        }

    async def get_current_status(self):
        return await super()._get_current_status(const.SOFTWARE_UPDATE_ID)
