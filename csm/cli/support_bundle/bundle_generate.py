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
from typing import Dict, List
from csm.common import comm
from csm.common.payload import Yaml, Tar
from csm.core.blogic import const
from datetime import datetime
from csm.common.errors import CsmError
from csm.common.conf import Conf
from csm.common.log import Log

ERROR= "error"
INFO = "info"

class ComponentsBundle:
    """
    This class handles generation for support bundles for different components.
    """
    @staticmethod
    def publish_log(msg, level, bundle_id, node_name, comment):
        """
        Format and Publish Log to ElasticSearch via Rsyslog.
        :param msg: Message to Be added :type: str.
        :param bundle_id: Unique Bundle Id for the Bundle :type:str.
        :param level: Level for the Log. :type: Log.ERROR/LOG.INFO.
        :param node_name: Name of the Node where this is running :type:str.
        :param comment: Comment Added by user to Generate the Bundle :type:str.
        :return: None.
        """
        Log.init("support_bundle",
                 syslog_server=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_server"),
                 syslog_port=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_port"),
                 backup_count=Conf.get(const.CSM_GLOBAL_INDEX, "Log.total_files"),
                 file_size_in_mb=Conf.get(const.CSM_GLOBAL_INDEX,
                                          "Log.file_size"),
                 log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path"),
                 level=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_level"))
        result = "Success"
        if level == 'error':
            result = "Error"
        message = f"{const.SUPPORT_BUNDLE_TAG}|{bundle_id}|{node_name}|{comment}|{result}|{msg}"
        Log.support_bundle(message)

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
    def send_file(protocol_details: Dict, file_path: str):
        """
        Method to send the tar files ove FTP Location.
        :param protocol_details: Dictionary of FTP Details. :type:dict
        :param file_path: Path of tar file to be sent. :type:str
        :return:
        """
        url = protocol_details.get('url')
        protocol = url.split("://")[0]
        channel = f"{protocol.upper()}Channel"
        if hasattr(comm, channel):
            try:
                channel_obj = getattr(comm, channel)(**protocol_details)
                channel_obj.connect()
                channel_obj.send_file(file_path, protocol_details.get('remote_file'))
                channel_obj.disconnect()
            except Exception as e:
                Log.error(f"File Upload Failed. {e}")
        else:
            Log.error("Invalid Url.")

    @staticmethod
    async def init(command: List):
        """
        Initializes the Process of Support Bundle Generation for Every Component.
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        bundle_id = command.options.get("bundle_id", "")
        node_name = command.options.get("node_name", "")
        comment = command.options.get("comment", "")
        #Read Commands.Yaml and Check's If It Exists.
        support_bundle_config = Yaml(const.COMMANDS_FILE).load()
        if not support_bundle_config:
            Log.error(f"No Such File {const.COMMANDS_FILE}, {ERROR}, {bundle_id},"
                      f" {node_name}, {comment}")
            ComponentsBundle.publish_log(f"No Such File {const.COMMANDS_FILE}",
                                         ERROR, bundle_id, node_name, comment)
            return None
        #Path Location for creating Support Bundle.
        path = os.path.join(Conf.get(const.CSM_GLOBAL_INDEX,
                                     "SUPPORT_BUNDLE.bundle_path"))
        if os.path.isdir(path):
            shutil.rmtree(path)
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
        directory_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                  "SUPPORT_BUNDLE.bundle_path")
        tar_file_name = os.path.join(directory_path, '../',
                                     f"{bundle_id}_{node_name}.tar.gz")
        #Create Summary File for Tar.
        summary_file_path = os.path.join(directory_path, "summary.yaml")
        summary_data = {
            "Bundle Id": str(bundle_id),
            "Node Name": str(node_name),
            "Comment": repr(comment),
            "Generated Time": str(datetime.isoformat(datetime.now()))
        }
        Yaml(summary_file_path).dump(summary_data)
        symlink_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                "SUPPORT_BUNDLE.symlink_path")
        if os.path.exists(symlink_path):
            shutil.rmtree(symlink_path)
        os.mkdir(symlink_path)

        # Wait Until all the Threads Execution is not Complete.
        for each_thread in threads:
            each_thread.join(timeout=1800)
        # Generate TAR FILE & Create Softlink for Generated TAR.
        try:
            Tar(tar_file_name).dump([path])
            os.symlink(tar_file_name, os.path.join(symlink_path,
                                                   f"SupportBundle.{bundle_id}"))
        except Exception as e:
            Log.error(
                f"Linking Failed, {e} {ERROR}, {bundle_id}, {node_name}, {comment}")
            ComponentsBundle.publish_log(f"Linking Failed {e}", ERROR, bundle_id,
                                         node_name,
                                         comment)
            return None

        #Upload the File.
        try:
            ComponentsBundle.send_file(Conf.get(const.CSM_GLOBAL_INDEX,
                                                "SUPPORT_BUNDLE"), tar_file_name)
            Log.info(f"Bundle Generated., {INFO}, {bundle_id}, {node_name}, {comment}")
            ComponentsBundle.publish_log("Bundle Generated.", INFO, bundle_id,
                                         node_name, comment)
        except Exception as e:
            Log.error(f"{e}, {ERROR}, {bundle_id}, {node_name}, {comment}")
            ComponentsBundle.publish_log(f"{e}", ERROR, bundle_id, node_name,
                                         comment)