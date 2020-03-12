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

import os
from marshmallow import Schema, fields
from csm.core.blogic import const
from csm.common.conf import Conf
from csm.common.log import Log
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.common.services import Service, ApplicationService

 
class HotfixApplicationService(ApplicationService):
    def __init__(self, fw_folder, provisioner_plugin):
        self._fw_file = os.path.join(fw_folder,'hotfix_fw_candidate')
        self._provisioner_plugin = provisioner_plugin

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

        try:
            file_ref.save_file(os.path.dirname(self._fw_file),
                os.path.basename(self._fw_file), True)
        except Exception as e:
            raise CsmInternalError(f'Failed to save the package: {e}')

        return {
            "version": info.version
        }

    async def start_upgrade(self):
        """
        Kicks off the hotfix application process
        :returns: Nothing
        """
        if not os.path.exists(self._fw_file):
            raise InvalidRequest('There is no uploaded firmware package')

        await self._provisioner_plugin.trigger_software_upgrade(self._fw_file)
