#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          upgrade.py
 Description:       Services for upgrade functionality

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
from csm.common.log import Log
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.common.services import Service, ApplicationService
from csm.core.data.models.upgrade import PackageInformation, UpdateStatusEntry
from csm.core.repositories.update_status import UpdateStatusRepository


class HotfixApplicationService(ApplicationService):
    SOFTWARE_UPDATE_ID = 'software_update'
    def __init__(self, fw_folder, provisioner_plugin, hotfix_repo):
        self._fw_file = os.path.join(fw_folder, 'hotfix_fw_candidate.iso')
        self._provisioner_plugin = provisioner_plugin
        self._hotfix_repo = hotfix_repo

    @Log.trace_method(Log.DEBUG)
    async def _get_renewed_model(self) -> UpdateStatusEntry:
        """
        Fetch the most up-to-date information about the most recent software upgrade process.
        Queries the DB, then queries the Provisioner if needed.
        """
        model = await self._hotfix_repo.get_current_model(self.SOFTWARE_UPDATE_ID)
        if model and model.is_in_progress():
            try:
                result = await self._provisioner_plugin.get_provisioner_job_status(model.provisioner_id)
                model.apply_status_update(result)
                await self._hotfix_repo.save_model(model)
            except:
                raise CsmInternalError(f'Failed to fetch the status of an ongoing upgrade process')

        return model

    @Log.trace_method(Log.INFO)
    async def get_current_status(self):
        """
        Fetch current state of hotfix update process.
        Synchronizes it with the Provisioner service if necessary.

        Returns {} if there is no information (e.g. because CSM has never been updated)
        Otherwise returns a dictionary that describes the process
        """
        model = await self._get_renewed_model()
        if not model:
            return {}

        return model.to_printable()

    @Log.trace_method(Log.INFO)
    async def upload_package(self, file_ref) -> PackageInformation:
        """
        Upload and validate a hotfix update firmware package
        :param file_ref: An instance of FileRef class that represents a new upgrade package
        :returns: An instance of PackageInformation
        """
        try:
            info = await self._provisioner_plugin.validate_hotfix_package(file_ref.get_file_path())
        except CsmError:
            raise InvalidRequest('You have uploaded an invalid hotfix firmware package')

        model = await self._get_renewed_model()
        if model and model.is_in_progress():
            raise InvalidRequest("You can't upload a new package while there is an ongoing upgrade")

        model = UpdateStatusEntry.generate_new(self.SOFTWARE_UPDATE_ID)
        model.version = info.version
        model.description = info.description
        model.mark_uploaded()
        await self._hotfix_repo.save_model(model)

        try:
            file_ref.save_file(os.path.dirname(self._fw_file),
                os.path.basename(self._fw_file), True)
        except Exception as e:
            raise CsmInternalError(f'Failed to save the package: {e}')

        return {
            "version": info.version,
            "description": info.description
        }

    @Log.trace_method(Log.INFO)
    async def start_upgrade(self):
        """
        Kicks off the hotfix application process
        :returns: Nothing
        """
        model = await self._get_renewed_model()
        if not model:
            raise CsmInternalError("Internal DB is iconsistent. Please upload the package again")

        if model.is_in_progress():
            raise InvalidRequest("Software upgrade is already in progress. Please wait until it is done.")

        if not model.is_uploaded() or not os.path.exists(self._fw_file):
            raise InvalidRequest("You must upload an image before starting the software upgrade.")

        model.provisioner_id = await self._provisioner_plugin.trigger_software_upgrade(self._fw_file)
        model.mark_started()
        await self._hotfix_repo.save_model(model)

        return {
            "message": "Software upgrade has succesfully started"
        }
