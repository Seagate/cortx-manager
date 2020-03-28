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

import re
from csm.common.process import SimpleProcess
from csm.common.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.common.errors import CsmInternalError, CsmError

class StorageCapacityService(ApplicationService):
    def __init__(self, provisioner):
        self._provisioner = provisioner
    """
    Service for Get disk capacity details
    """

    @staticmethod
    async def unit_conversion(capacity):
        """
        Method to dynamically convert byte data in KB/MB/GB ... YB.

        :param capacity: Disk size in bytes :type: int
        :return: :type: str
        """
        for unit in const.UNIT_LIST:
            capacity = capacity / 1024
            if capacity / 100 < 10:
                break

        return f'{round(capacity, 2)} {unit}'

    @Log.trace_method(Log.DEBUG)
    async def get_capacity_details(self):
        """
        This method will return system disk details as per command
        :return: dict
        """
        try:
            process = SimpleProcess(const.M0_CLUSTER_SIZE_CMD)
            stdout, stderr, rc = process.run()
        except Exception as e:
            raise CsmInternalError(f"Error in command execution command : {e}")
        if not stdout or rc!=0:
            raise CsmInternalError(f"Failed to process command : {stderr.decode('utf-8')}"
                                   f"-{stdout.decode('utf-8')}")
        Log.debug(f"{const.M0_CLUSTER_SIZE_CMD} command output stdout:{stdout}")
        console_output = re.sub(' +', ' ', stdout.decode('utf-8')).split('\n')
        cropped_console_data = [str(each_element).strip() for each_element in
                                console_output if "space" in each_element]
        capacity_info = {data.split()[0]+data.split()[1] : int(data.split()[2])
                         for data in cropped_console_data}
        formatted_output = {}
        formatted_output[const.SIZE] = await self.unit_conversion(capacity_info[const.TOTAL_SPACE])
        formatted_output[const.USED] = await self.unit_conversion(
            capacity_info[const.TOTAL_SPACE] - capacity_info[const.FREE_SPACE])
        formatted_output[const.AVAILABLE] = await self.unit_conversion(capacity_info[const.FREE_SPACE])
        formatted_output[const.USAGE_PERCENTAGE ] = str(
            100 - round((capacity_info[const.FREE_SPACE] / capacity_info[const.TOTAL_SPACE]) * 100, 2)) + ' %'
        return formatted_output
