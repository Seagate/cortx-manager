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

import os


class FirmwareUpdateService(ApplicationService):
    """
    Service for firmware package upload
    """

    def __init__(self, provisioner, fw_storage_path: str):
        self._provisioner = provisioner
        self._fw_storage_path = fw_storage_path

    async def firmware_package_upload(self, package_ref, filename):
        """
        Service to upload and validate firmware package. Also returns last
        firmware ugrade status
        :param package_ref: FileRef object
        :param filename: str
        :return: dict
        """
        # TODO: Changes required as per provisioner api to validate the package
        firmware_package_path = package_ref.save_file(self._fw_storage_path, filename, True)
        upload_status = await self._provisioner.validate_package(firmware_package_path)
        # TODO: If package is valid then filename will be stored in config for future reference
        Conf.set(const.CSM_GLOBAL_INDEX, "UPDATE.valid_firmware_package_name", filename)
        Conf.set(const.CSM_GLOBAL_INDEX, "UPDATE.valid_firmware_package_version", 
                 upload_status['version'])
        # TODO: If package is invalid it will be deleted. 
        # Delete functionality is implemented.
        last_upgrade_status = await self._provisioner.get_last_firmware_upgrade_status()

        return {"upload_status": upload_status,
                "last_upgrade_status": last_upgrade_status}

    async def trigger_firmware_upload(self, fw_package):
        """
        Service to trigger firmware upgrade
        :return:
        """
        # TODO: Changes required as per provisioner api to trigger firmware upload 
        return await self._provisioner.trigger_firmware_upload(fw_package)

    async def check_for_package_availibility(self):
        """
        Service to check package is available at configured path
        :return: dict
        """
        fw_package_info = Conf.get(const.CSM_GLOBAL_INDEX, "UPDATE")
        if not (fw_package_info.get('valid_firmware_package_name') and \
                    os.path.exists(os.path.join(fw_package_info.get('firmware_store_path'), 
                                    fw_package_info.get('valid_firmware_package_name','')))):
            fw_package_info["is_available"] = False
            return fw_package_info   
        fw_package_info["is_available"] = True
        return fw_package_info
