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
        os.makedirs(storage_path, exist_ok=True)

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
        model.version = os.path.splitext(os.path.basename(filename))[0]
        model.description = os.path.join(self._fw_storage_path, filename)
        model.file_path = os.path.join(self._fw_storage_path, filename)
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

        firmware_update_model.provisioner_id = await self._provisioner.trigger_firmware_update(firmware_update_model.file_path)
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
        if not model.file_path or not os.path.exists(model.file_path):
            raise InvalidRequest(f"Firmware package {model.file_path} not found.")
        return model.to_printable()

    async def get_current_status(self):
        return await super()._get_current_status(const.FIRMWARE_UPDATE_ID)