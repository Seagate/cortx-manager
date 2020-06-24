#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          version.py
 Description:       Services for product version details.

 Creation Date:     06/11/2020
 Author:            Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.common.services import ApplicationService
from eos.utils.log import Log

class ProductVersionService(ApplicationService):
    """
    Service for product version information
    """
    
    def __init__(self, provisioner):
        self._provisioner = provisioner
    
    async def get_current_version(self):
        """
        Fetch current installed product version information using 
        provisioner plugin.
        :returns: Dict having installed product version.
        """
        return await self._provisioner.get_current_version()