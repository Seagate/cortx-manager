#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          bundle_generate.py
 Description:       Creates the Bundles for Each node and Uploads it to Remote
                    FTP location.

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
import threading
import shutil
import errno
from typing import Dict, List
from csm.common import comm
from csm.common.payload import Yaml, Tar
from csm.core.blogic import const
from csm.common.errors import CsmError
from csm.common.conf import Conf
from csm.common.log import Log

class ComponentsBundle:
    """
    This class handles generation for support bundles for different components.
    """
    @staticmethod
    def exc_components_cmd(commands: List, bundle_id: str, path: str):
        """
        Executes the Command for Bundle Generation of Every Component.
        :param commands: Command of the component :type:str
        :param bundle_id: Unique Bundle ID of the generation process. :type:str
        :param path: Path to create the tar by components :type:str
        :return:
        """
        for command in commands:
            os.system(f"{command} {bundle_id} {path}")

    @staticmethod
    def send_file(protocol_details: Dict, file_url: str):
        """
        Method to send the tar files ove FTP Location.
        :param protocol_details: Dictionary of FTP Details. :type:dict
        :param file_url: Name of tar file to be sent. :type:str
        :return:
        """
        channel = f"{protocol_details.get('protocol')}Channel"
        if hasattr(comm, channel):
            channel_obj = getattr(comm, channel)(**protocol_details)
            channel_obj.connect()
            channel_obj.send_file(file_url, protocol_details.get('remote_file'))

    @staticmethod
    def init(command: List):
        """
        Initializes the Process of Support Bundle Generation for Every Component.
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        support_bundle_config = Yaml(const.COMMANDS_FILE).load()
        if not support_bundle_config:
            CsmError(rc=errno.ENOENT,  message_id=_("No Such File {}"),
                     message_args=(const.COMMANDS_FILE))
        bundle_id = command.options.get("bundle_id")
        node_name = command.options.get("node_name")
        path = os.path.join(Conf.get(const.CSM_GLOBAL_INDEX,
                         "SUPPORT_BUNDLE.bundle_path"),bundle_id)
        if os.path.isdir(path):
            os.rmdir(path)
        os.makedirs(path)

        # Start Execution for each Component Command.
        threads = []
        for each_component in support_bundle_config.get("COMMANDS"):
            components_commands = []
            file_data = Yaml(each_component).load()
            if file_data:
                components_commands = file_data.get("support_bundle", [])
            if components_commands:
                thread_obj = threading.Thread(ComponentsBundle.exc_components_cmd(
                    components_commands, bundle_id, path))
                thread_obj.start()
                threads.append(thread_obj)

        tar_file_name = os.path.join(Conf.get(const.CSM_GLOBAL_INDEX,
                         "SUPPORT_BUNDLE.bundle_path"),
                                     f"{bundle_id}_{node_name}.tar.gz")

        # Wait Until all the Threads Execution is not Complete.
        for each_thread in threads:
            each_thread.join(timeout=1800)

        # Generate TAR FILE & Send the File to Given FTP location.
        try:
            Tar(tar_file_name).dump([path])
            ComponentsBundle.send_file(Conf.get(const.CSM_GLOBAL_INDEX,
                                "SUPPORT_BUNDLE"),tar_file_name)
        except Exception as e:
            Log.publish(const.SUPPORT_BUNDLE_TAG, log_level="error"
                        f"{e}")
        finally:
            if os.path.exists(tar_file_name):
                os.remove(tar_file_name)
            if os.path.exists(path):
                shutil.rmtree(path)
            Log.publish(const.SUPPORT_BUNDLE_TAG, "Support Bundle Generation Successful.")
