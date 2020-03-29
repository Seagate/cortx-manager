#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          provisioner.py
 Description:       Contains the implementation of Provisioner plugin.

 Creation Date:     02/25/2020
 Author:            Udayan Yaragattikar, Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio
import datetime
from concurrent.futures import ThreadPoolExecutor
from csm.common.log import Log
from csm.core.blogic import const
from csm.common.errors import InvalidRequest, CsmInternalError
from csm.core.data.models.upgrade import PackageInformation, ProvisionerStatusResponse, ProvisionerCommandStatus
from csm.core.blogic.const import PILLAR_GET
try:
    from salt import client
except Exception as e:
    client = None
    Log.error(f"Salt.client not initilized: {e}")

class PackageValidationError(InvalidRequest):
    pass


class ProvisionerPlugin:
    """
    Plugin that provides provisioner's api integration.
    """
    def __init__(self, username=None, password=None):
        try:
            import provisioner
            import provisioner.freeze

            self.provisioner = provisioner
            Log.info("Provisioner plugin is loaded")

            if username and password:
                self.provisioner.auth_init(
                    username=username,
                    password=password,
                    eauth="pam"
                )
        except Exception as error:
            self.provisioner = None
            Log.error(f"Provisioner module not found : {error}")

    async def _await_nonasync(self, func):
        pool = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(pool, func)

    @Log.trace_method(Log.DEBUG)
    async def validate_hotfix_package(self, path) -> PackageInformation:
        """
        Validate an update image
        :param path: Path to the image file
        :returns: a PackageInformation object
        :raises: PackageValidationError in case of an invalid package
        """
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                # The version argument has no effect here, but we need to pass it anyway
                version = self._generate_random_version()
                self.provisioner.set_eosupdate_repo(version, path, dry_run=True)
            except self.provisioner.errors.ProvisionerError as e:
                raise PackageValidationError(f"Package validation failed: {e}")

        await self._await_nonasync(_command_handler)

        # TODO: fix it once it is ready on the provisioner side
        validation_result = PackageInformation()
        validation_result.version = 'uknown_ver'
        validation_result.description = 'unknown_desc'
        return validation_result

    @Log.trace_method(Log.DEBUG)
    async def trigger_software_upgrade(self, path):
        """
        Starts the software update.
        :param path: Path to a file that contains the update image
        :returns: Value which will later be used to poll for the status of the process
        """

        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                # Generating the version here as at the moment we cannot infer it from the package
                version = self._generate_random_version()
                self.provisioner.set_eosupdate_repo(version, path)
                return self.provisioner.eos_update(nowait=True)
            except Exception as e:
                Log.exception(e)
                raise CsmInternalError('Failed to start the upgrade process')

        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def get_upgrade_status(self, query_id) -> ProvisionerStatusResponse:
        """
        Polls Provisioner for the status of a software and firmware update process
        """
        def _command_handler():
            # TODO: separately handle the case when the problem is related to the communication to the provisioner
            try:
                self.provisioner.get_result(query_id)
                return ProvisionerStatusResponse(ProvisionerCommandStatus.Success)
            except self.provisioner.errors.PrvsnrCmdNotFinishedError:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.InProgress)
            except self.provisioner.errors.PrvsnrCmdNotFoundError:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.NotFound)
            except:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.Failure)

        return await self._await_nonasync(_command_handler)

    def _generate_random_version(self):
        return datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")

    async def validate_package(self, file_path):
        # TODO: Provisioner api to validate package tobe implented here
        Log.debug(f"Validating package: f{file_path}")
        return {"version": "1.2.3",
                "file_path": file_path}

    async def trigger_firmware_upgrade(self, fw_package_path):
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                return self.provisioner.fw_update(source = fw_package_path, nowait = True)
            except Exception as e:
                Log.exception(e)
                raise CsmInternalError('Failed to start the upgrade process')

        return await self._await_nonasync(_command_handler)

    async def set_ntp(self, ntp_data: dict):
        """
        Set ntp configuration using provisioner api.
        :param ntp_data: Ntp config dict 
        :returns:
        """
        # TODO: Exception handling as per provisioner's api response
        try:
            if (ntp_data.get(const.NTP_SERVER_ADDRESS, None) and 
                    ntp_data.get(const.NTP_TIMEZONE_OFFSET, None)):
                if self.provisioner:
                    Log.debug("Handling provisioner's set ntp api request")
                    self.provisioner.set_ntp(server=ntp_data[const.NTP_SERVER_ADDRESS], 
                                timezone=ntp_data[const.NTP_TIMEZONE_OFFSET].split()[-1])
        except self.provisioner.errors.ProvisionerError as error:
            Log.error(f"Provisioner api error : {error}")

    async def get_node_list(self):
        node_list = client.Caller().function(PILLAR_GET, 'cluster:node_list')
        return node_list if node_list else []

    async def is_primary_node(self, node_id):
        return client.Caller().function(PILLAR_GET, f'cluster:{node_id}:is_primary')

    async def get_node_details(self, node_name):
        node_details = client.Caller().function(PILLAR_GET, f'cluster:{node_name}')
        return node_details if node_details else {}

    async def get_provisioner_status(self, status_type):
        # TODO: Provisioner api to get status tobe implented here
        Log.debug(f"Getting provisioner status for : {status_type}")
        return {"status": "Successful"}
