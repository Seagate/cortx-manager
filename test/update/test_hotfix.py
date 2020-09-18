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

import asyncio
import sys
import os
import json
import unittest
import datetime
from unittest.mock import patch
from contextlib import contextmanager

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.payload import Json, Payload
from cortx.utils.log import Log
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.core.data.models.upgrade import PackageInformation, UpdateStatusEntry
from csm.core.data.models.upgrade import (PackageInformation, ProvisionerStatusResponse,
                                          ProvisionerCommandStatus)
from csm.core.repositories.update_status import UpdateStatusRepository
from csm.core.services.hotfix_update import HotfixApplicationService


t = unittest.TestCase()

class CustomUpdateStatusRepo:
    """
    Repository that keeps a single instance of a UpdateStatusEntry model for each update type.
    """
    def __init__(self):
        self.models = {}

    async def get_current_model(self, update_type: str) -> UpdateStatusEntry:
        return self.models.get(update_type, None)

    async def save_model(self, model: UpdateStatusEntry):
        t.assertTrue(isinstance(model, UpdateStatusEntry), "Only UpdateStatusEntry may be saved")
        t.assertIsNotNone(model.update_type)
        model.updated_at = datetime.datetime.now()
        self.models[model.update_type] = model

    async def drop_model(self, update_type: str) -> UpdateStatusEntry:
        self.models[update_type] = None


class ProvisionerMock:
    def __init__(self):
        self.validation_response = None
        self.trigger_result = True
        self.provisioner_status = None

    async def validate_hotfix_package(self, path, file_name) -> PackageInformation:
        if self.validation_response:
            return self.validation_response
        raise CsmError(f"Package validation failed")

    async def trigger_software_upgrade(self, path):
        if not self.trigger_result:
            raise CsmError("Failed to start upgrade. Try again.")

    async def get_provisioner_job_status(self, query_id: str) -> ProvisionerStatusResponse:
        return self.provisioner_status


class FileRefMock():
    def __init__(self, file_path):
        self.path = file_path

    def get_file_path(self) -> str:
        return self.path

    def save_file(self, dir_to_save, filename, overwrite=False):
        pass


@contextmanager
def patch_io(*args, **kwds):
    # Code to acquire resource, e.g.:
    resource = acquire_resource(*args, **kwds)
    try:
        yield resource
    finally:
        # Code to release resource, e.g.:
        release_resource(resource)

validation_result = PackageInformation()
validation_result.version = '1.2.3'
validation_result.description = 'Some description'

mock_file = FileRefMock('/tmp/abcd.txt')  # File name doesn't matter

def init(args):
    """ test initialization """
    pass

async def test_validation(args=None):
    """
    Preconditions: no UpdateStatusEntry

    1. "Upload" an invalid package
    2. Check that an exception is raised and no UpdateStatusEntry created
    3. "Upload" a valid package
    4. Check that a new model is created and no exceptions are raised
    """
    repo = CustomUpdateStatusRepo()
    plugin = ProvisionerMock()
    plugin.validation_response = None

    service = HotfixApplicationService('/tmp', plugin, repo)
    with t.assertRaises(InvalidRequest):
        await service.upload_package(mock_file, 'abcd.iso')

    status = await service.get_current_status()
    t.assertEqual(status, {})

    plugin.validation_response = validation_result
    result = await service.upload_package(mock_file, 'abcd.iso')

    status = await service.get_current_status()
    t.assertNotEqual(status, {})
    t.assertEqual(status["status"], "uploaded")
    t.assertEqual(status["version"], validation_result.version)
    t.assertEqual(status["description"], validation_result.description)


async def test_duplicate_upload(args=None):
    """
    1. Attempt upload while there is an UpdateStatusEntry with in_progres status
    2. Attempt upload while there is an UpdateStatusEntry with uploaded status
    3. It must not throw an exception
    """
    repo = CustomUpdateStatusRepo()
    plugin = ProvisionerMock()
    plugin.validation_response = validation_result
    service = HotfixApplicationService('/tmp', plugin, repo)

    await service.upload_package(mock_file, 'abcd.iso')

    status = await service.get_current_status()
    t.assertEqual(status["status"], "uploaded")
    await service.upload_package(mock_file, 'abcd.iso')


async def _setup_uploaded_file():
    repo = CustomUpdateStatusRepo()
    plugin = ProvisionerMock()
    plugin.validation_response = validation_result
    plugin.provisioner_status = ProvisionerStatusResponse(ProvisionerCommandStatus.InProgress)
    service = HotfixApplicationService('/tmp', plugin, repo)

    await service.upload_package(mock_file, 'abcd.iso')
    status = await service.get_current_status()
    t.assertEqual(status["status"], "uploaded")

    return (service, plugin)


async def test_hotfix_flow(args=None):
    """
    1. Upload a package.
    2. Call get_current_status, validate
    3. Start update
    4. Call get_current_status, validate
    5. Mock get_provisioner_job_status to return success
    6. Call get_current_status, validate
    7. Check that it is possible to upload a file again
    """
    service, plugin = await _setup_uploaded_file()

    with patch('os.path.exists') as patched:
        patched.return_value = True
        await service.start_upgrade()

    status = await service.get_current_status()
    t.assertEqual(status["status"], "in_progress")

    plugin.provisioner_status = ProvisionerStatusResponse(ProvisionerCommandStatus.Success)
    status = await service.get_current_status()
    t.assertEqual(status["status"], "success")

    await service.upload_package(mock_file, 'abcd.iso')
    status = await service.get_current_status()
    t.assertEqual(status["status"], "uploaded")


async def test_hotfix_flow_fail(args=None):
    """
    1. Upload a package.
    2. Call get_current_status, validate
    3. Start update
    4. Call get_current_status, validate
    5. Mock get_provisioner_job_status to return fail
    6. Call get_current_status, validate
    7. Test that it is possible to upload a package again
    """
    service, plugin = await _setup_uploaded_file()

    with patch('os.path.exists') as patched:
        patched.return_value = True
        await service.start_upgrade()

    status = await service.get_current_status()
    t.assertEqual(status["status"], "in_progress")

    plugin.provisioner_status = ProvisionerStatusResponse(ProvisionerCommandStatus.Failure)
    status = await service.get_current_status()
    t.assertEqual(status["status"], "fail")

    await service.upload_package(mock_file, 'abcd.iso')
    status = await service.get_current_status()
    t.assertEqual(status["status"], "uploaded")


async def test_duplicate_update(args=None):
    """
    1. Upload a package
    2. Start upgrade.
    3. Call get_current_status, validate
    4. Start upgrade. Validate error.
    """
    service, plugin = await _setup_uploaded_file()

    with patch('os.path.exists') as patched:
        patched.return_value = True
        await service.start_upgrade()

        with t.assertRaises(InvalidRequest):
            await service.start_upgrade()


async def test_upload_after_start(args=None):
    """
    1. Upload a package
    2. Start upgrade.
    3. Upload again
    """
    service, plugin = await _setup_uploaded_file()

    with patch('os.path.exists') as patched:
        patched.return_value = True
        await service.start_upgrade()

    status = await service.get_current_status()
    t.assertEqual(status["status"], "in_progress")
    with t.assertRaises(InvalidRequest):
        await service.upload_package(mock_file, 'abcd.iso')


async def test_failed_trigger_update(args=None):
    """
    1. Upload a package
    2. Start upgrade. It fails to start.
    4. Validate the status
    """
    service, plugin = await _setup_uploaded_file()
    plugin.trigger_result = False

    with patch('os.path.exists') as patched:
        patched.return_value = True
        with t.assertRaises(CsmError):
            await service.start_upgrade()

    status = await service.get_current_status()
    t.assertEqual(status["status"], "uploaded")


def run_tests(args = {}):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_validation())
    loop.run_until_complete(test_duplicate_upload())
    loop.run_until_complete(test_hotfix_flow())
    loop.run_until_complete(test_hotfix_flow_fail())
    loop.run_until_complete(test_duplicate_update())
    loop.run_until_complete(test_upload_after_start())
    loop.run_until_complete(test_failed_trigger_update())

test_list = [run_tests]

if __name__ == '__main__':
    Log.init('test',  log_path=".")
    run_tests()
