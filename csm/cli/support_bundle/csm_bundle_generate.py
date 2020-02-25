#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          csm_bundle_generate.py
 Description:       Command to generate the Bundle for CSM logs.

 Creation Date:     29/01/2020
 Author:            Prathamesh Rodi


 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
from csm.core.blogic import const
from csm.common.payload import Yaml, Tar
from csm.common.conf import Conf

class CSMBundle:
    """
    ThiS Class generates the Support Bundle for Component CSM.

    Currently Included Files in CSM Support Bundle:-
    1) csmcli.log -- Logs for CLI .
    2) csm_agent.log -- Logs for CSM Backend Agent.
    3) csm_setup.log -- Logs generated during setup for CSM Component.
    """

    @staticmethod
    async def init(command):
        """
        This method will generate bundle for CSM and include the logs in it.
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        # Read Config to Fetch Log File Path
        log_directory_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path")
        # Creates CSM Directory
        path = command.options.get("path")
        bundle_id = command.options.get("bundle_id")
        path = os.path.join(path, const.CSM_GLOBAL_INDEX)
        os.makedirs(path)
        # Generate Tar file for Logs Folder.
        tar_file_name = os.path.join(path, f"csm_{bundle_id}.tar.gz")
        Tar(tar_file_name).dump([log_directory_path])


