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

from csm.common.errors import CsmInternalError
from csm.common.fs_utils import FSUtils
from csm.common.services import ApplicationService
from cortx.utils.log import Log

class UpdateService(ApplicationService):

    def __init__(self, provisioner, update_repo):
        self._provisioner = provisioner
        self._update_repo = update_repo

    async def upload_package(self, package_ref, **kwargs):
        raise NotImplementedError

    async def start_update(self):
        raise NotImplementedError

    async def get_current_status(self):
        raise NotImplementedError

    @Log.trace_method(Log.DEBUG)
    async def _get_renewed_model(self, update_id):
        """
        Fetch the most up-to-date information about the most recent firmware and software update process.
        Queries the DB, then queries the Provisioner if needed.
        """
        model = await self._update_repo.get_current_model(update_id)
        if model and model.is_in_progress():
            try:
                result = await self._provisioner.get_provisioner_job_status(model.provisioner_id)
                model.apply_status_update(result)
                if model.is_successful():
                    fw_path = os.path.splitext(model.file_path)[0]
                    fw_dir = os.path.dirname(fw_path)
                    Log.info(f'Cleaning update directory \"{fw_dir}\" contents')
                    FSUtils.clear_dir_contents(fw_dir)
                    # FIXME: temporary solution, until the provisioner returns the proper version
                    version = os.path.basename(fw_path)
                    model.version = version
                    Log.info(f"Version : {version} :: FW Directory Path :{fw_dir}")
                await self._update_repo.save_model(model)
                Log.info(f'Save renewed model for {update_id} for provisioner_id:{model.provisioner_id}:{model.to_printable()}')
            except Exception as e:
                Log.error(f'Failed to fetch the status of an ongoing update process: {e}')
                raise CsmInternalError('Failed to fetch the status of an ongoing update process')
        return model


    @Log.trace_method(Log.INFO)
    async def _get_current_status(self, update_id):
        """
        Fetch current state of firmware and hotfix update process.
        Synchronizes it with the Provisioner service if necessary.

        Returns {} if there is no information (e.g. because CSM has never been updated)
        Otherwise returns a dictionary that describes the process
        """
        model = await self._get_renewed_model(update_id)
        if not model:
            Log.info(f"No Model Found for Update ID : {update_id}")
            return {}

        return model.to_printable()
