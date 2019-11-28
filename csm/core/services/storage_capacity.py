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
from csm.core.providers.providers import Response


class StorageCapacityService(ApplicationService):
    """
    Service for Get disk capacity details
    """

    @Log.trace_method(Log.DEBUG)
    async def get_capacity_details(self):
        """
        This method will return system disk details as per command
        :return: dict
        """
        # TODO: 'hctl mero status' command will be changed when HALON is replaced with HARE
        process = subprocess.Popen(['hctl','mero','status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if not stdout:
            Log.error(stderr)
            return Response(rc=422, output=f"{stderr}")

        data_list = [str(space).strip() for space in (re.sub(' +', ' ', stdout.decode('utf-8')).split('\n')) if ("space") in str(space)]

        data_dict = {key:int(val.replace(',','')) for key,val in (data.split(':') for data in data_list) }

        formatted_output_dict = {}
        formatted_output_dict['size'] = str(round(data_dict['Total space'] / (1024**3),2)) + ' GB'
        formatted_output_dict['used'] = str(round((data_dict['Total space'] - data_dict['Free space']) / (1024**3),2)) + ' GB'
        formatted_output_dict['avail'] = str(round(data_dict['Free space'] / (1024**3),2)) + ' GB'
        formatted_output_dict['usage_percentage'] =  str(100- round( (data_dict['Free space'] / data_dict['Total space']) * 100 ,2)) + ' %'


        return  formatted_output_dict


