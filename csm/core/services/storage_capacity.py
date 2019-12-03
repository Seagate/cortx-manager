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
import subprocess

from csm.common.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.core.providers.providers import Response


class StorageCapacityService(ApplicationService):
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

        # TODO: 'hctl mero status' command will be changed when HALON is replaced with HARE
        process = subprocess.Popen(const.HCTL_COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if not stdout:
            Log.error(stderr)
            return Response(rc=422, output=f"{stderr}")
        console_output = (re.sub(' +', ' ', stdout.decode('utf-8')).split('\n'))
        cropped_console_data = [str(each_element).strip() for each_element in console_output if
                                "space" in str(each_element)]
        capacity_info = {key: int(value.replace(',', '')) for key, value in
                         (data.split(':') for data in cropped_console_data)}
        formatted_output = {}
        formatted_output['size'] = await self.unit_conversion(capacity_info['Total space'])
        formatted_output['used'] = await self.unit_conversion(
            capacity_info['Total space'] - capacity_info['Free space'])
        formatted_output['avail'] = await self.unit_conversion(capacity_info['Free space'])
        formatted_output['usage_percentage'] = str(
            100 - round((capacity_info['Free space'] / capacity_info['Total space']) * 100, 2)) + ' %'

        return formatted_output
