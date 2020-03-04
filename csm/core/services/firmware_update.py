#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          storage_capacity.py
 Description:       Service(s) for getting disk capacity details

 Creation Date:     11/22/2019
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
import os

class FirmwareUpdateService(ApplicationService):
    """
    Service for firmware package upload
    """
    def __init__(self, provisioner, fw_storage_path: str):
        self._provisioner = provisioner
        self._fw_storage_path = fw_storage_path
        
        
    async def firmware_package_upload(self, package_ref,filename):
        cache_path =  os.path.join(package_ref.cache_dir, package_ref.file_uuid)
        firmware_package_path = package_ref.save_file(self._fw_storage_path, filename, True)
        return await self._provisioner.validate_package(firmware_package_path)

    async def trigger_firmware_upload(self):

        return await self._provisioner.trigger_firmware_upload()

