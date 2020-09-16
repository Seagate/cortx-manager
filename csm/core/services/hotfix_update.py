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

import os

from cortx.utils.log import Log

from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.core.blogic import const
from csm.core.data.models.upgrade import UpdateStatusEntry
from csm.core.services.update_service import UpdateService


class HotfixApplicationService(UpdateService):

    def __init__(self, storage_path, provisioner, update_repo):
        super().__init__(provisioner, update_repo)
        self._sw_file = os.path.join(storage_path, 'hotfix_fw_candidate.iso')
        os.makedirs(storage_path, exist_ok=True)

    @Log.trace_method(Log.INFO)
    async def upload_package(self, file_ref, file_name):
        """
        Upload and validate a hotfix update firmware package

        :param file_ref: An instance of FileRef class that represents a new update package
        :return: An instance of PackageInformation
        """

        try:
            info = await self._provisioner.validate_hotfix_package(
                file_ref.get_file_path(), file_name)
        except CsmError:
            raise InvalidRequest('You have uploaded an invalid software update package')

        model = await self._get_renewed_model(const.SOFTWARE_UPDATE_ID)
        if model and model.is_in_progress():
            raise InvalidRequest("You can't upload a new package while there is an ongoing update")

        model = UpdateStatusEntry.generate_new(const.SOFTWARE_UPDATE_ID)
        model.version = info.version
        model.file_path = os.path.join(os.path.dirname(self._sw_file), file_name)
        model.description = info.description
        model.mark_uploaded()
        Log.debug(model.to_printable())
        await self._update_repo.save_model(model)

        try:
            file_ref.save_file(os.path.dirname(self._sw_file), file_name, True)
        except Exception as e:
            raise CsmInternalError(f'Failed to save the package: {e}')

        return {
            "version": info.version,
            "description": info.description,
            "details": model.file_path
        }

    @Log.trace_method(Log.INFO)
    async def start_update(self):
        """
        Kicks off the hotfix application process

        :return: None
        """

        firmware_update_model = await self._get_renewed_model(const.FIRMWARE_UPDATE_ID)
        if firmware_update_model and firmware_update_model.is_in_progress():
            raise InvalidRequest(
                "Firmware update is already in progress. Please wait until it is done.")

        software_update_model = await self._get_renewed_model(const.SOFTWARE_UPDATE_ID)

        if software_update_model and software_update_model.is_in_progress():
            raise InvalidRequest(
                "Software update is already in progress. Please wait until it is done.")

        if (not software_update_model.is_uploaded()
                or not os.path.exists(software_update_model.file_path)):
            raise InvalidRequest("You must upload an image before starting the software update.")

        software_update_model.provisioner_id = await self._provisioner.trigger_software_update(
            software_update_model.file_path)
        software_update_model.mark_started()
        Log.debug(software_update_model.to_printable())
        await self._update_repo.save_model(software_update_model)
        return {"message": "Software update has successfully started"}

    async def get_current_status(self):
        return await super()._get_current_status(const.SOFTWARE_UPDATE_ID)
