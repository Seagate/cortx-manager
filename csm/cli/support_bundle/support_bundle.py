#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          support_bundle.py
 Description:       Support Bundle Generate and status Command

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

import sys
import os
import string
import random
import asyncio
import shutil
import errno
import getpass
from threading import Thread
from csm.common.payload import Yaml, JsonMessage
from csm.core.blogic import const
from csm.common.comm import SSHChannel
from csm.core.services.support_bundle import SupportBundleRepository
from eos.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.errors import CsmError
from csm.core.providers.providers import Response
from csm.common import errors
from csm.common.conf import Conf
from eos.utils.log import Log
import time
from csm.common.process import SimpleProcess

class SupportBundle:
    """
    This Class initializes the Support Bundle Generation for EOS.
    """

    @staticmethod
    def execute_ssh(ip_address: str, current_user: str, ssh_key: str,
                    command: str, node_name: str):
        """
        This Method makes Connection on each node and Executes Bundle Generation Command.
        For Using this Method Need to setup ssh keys in ~/.ssh/ folder.

        Please use the Following commands to do so.

        $ssh-keygen
        $ ssh-copy-id ./id_rsa.pub <username>@<host>

        Once Implemented the code will be able to connect to the node.

        :param ip_address: Ip Address of the Node. :type: str
        :param bundle_id: Unique ID of the Bundle needed to be generated. :type: str
        :param comment: Reason to generate the SB. :type: str
        :param node_name: Name of the NODE in EOS Term :type: str
        :param current_user : Local User Name for SSH :type str
        :param ssh_key: SSH Key Path :type str.
        :return:
        """
        try:
            ssh_conn_object = SSHChannel(ip_address, user=current_user,
                                         key_filename=ssh_key)
            ssh_conn_object.connect()

            try:
                # Executes Shell Script to Run in Background.
                # Time out releases the connection rather than waiting for cmd.
                # Since Shell Runs in Background no response is expected from Shell Command.
                Log.debug(f"Executing Command {command} -n {node_name} &")
                ssh_conn_object.execute(f"{command} -n {node_name} &", timeout=2)
            except CsmError:
                Log.debug(f"Started Bundle Generation on {ip_address}")
            ssh_conn_object.disconnect()
        except CsmError:
            sys.stderr.write(f"Could Not Connect to {ip_address}\n")

    @staticmethod
    async def fetch_host_from_salt():
        """
        This Method Fetchs Hostname for all nodes from Salt DB
        :return: hostnames : List of Hostname :type: List
        :return: node_list : : List of Node Name :type: List
        """
        process = SimpleProcess(
            "salt-call pillar.get cluster:node_list --out=json")
        _out, _err, _rc = process.run()
        if _rc != 0:
            Log.warn(f"Salt Command Failed : {_err}")
            return None, None
        output = JsonMessage(_out.strip()).load()
        nodes = output.get("local", [])
        hostnames = []
        for each_node in nodes:
            process = SimpleProcess(
                f"salt-call pillar.get cluster:{each_node}:hostname --out=json")
            _out, _err, _rc = process.run()
            if _rc != 0:
                Log.warn(f"Salt Command Failed : {_err}")
                return None, None
            output = JsonMessage(_out.strip()).load()
            hostnames.append(output.get("local", ""))
        return hostnames, nodes

    @staticmethod
    async def fetch_host_from_cluster():
        """
        This Method is Backup method for Reading Cluster.sls if Salt Read Fails.
        :return: hostnames : List of Hostname :type: List
        :return: node_list : : List of Node Name :type: List
        """
        Log.info("Falling back to reading cluster information from cluster.sls.")
        cluster_file_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                     "SUPPORT_BUNDLE.cluster_file_path")
        if not cluster_file_path or not os.path.exists(cluster_file_path):
            repsonse_msg = {"message": (f"{cluster_file_path} not Found. \n"
                                        f"Please check if cluster info file is correctly configured.")}
            return Response(rc=errno.ENOENT, output=repsonse_msg), None
        cluster_info = Yaml(cluster_file_path).load().get("cluster", {})
        active_nodes = cluster_info.get("node_list", [])
        if not active_nodes:
            response_msg = {
                "message": "No active nodes found. Cluster file may not be valid"}
            return Response(output=response_msg,
                            rc=errors.CSM_ERR_INVALID_VALUE), None
        hostnames = []
        for each_node in active_nodes:
            hostnames.append(cluster_info.get(each_node, {}).get("hostname"))
        return hostnames, active_nodes


    @staticmethod
    async def bundle_generate(command) -> sys.stdout:
        """
        Initializes the process for Generating Support Bundle on Each EOS Node.
        :param command: Csm_cli Command Object :type: command
        :return: None
        """
        current_user = str(getpass.getuser())
        # Check if User is Root User.
        if current_user.lower() != const.SSH_USER_NAME:
            repsonse_msg = f"Support Bundle {const.ROOT_PRIVILEGES_MSG}"
            return Response(rc=errno.EACCES, output=repsonse_msg)
        # Generate Unique Bundle ID
        alphabet = string.ascii_lowercase + string.digits
        bundle_id = f"SB{''.join(random.choices(alphabet, k=8))}"
        # Get Arguments From Command
        comment = command.options.get(const.SB_COMMENT)
        components = command.options.get(const.SB_COMPONENTS, [])
        sos = True if command.options.get(const.SOS_COMP, False) == "true" else False
        # Create Shell Command.
        shell_args = f"-i {bundle_id} -m {repr(comment)} "
        if sos:
            Log.debug("Generating OS Logs.")
            shell_args = f"{shell_args} -s"
        if components:
            if "all" not in components:
                Log.info(f"Generating Bundle for  {' '.join(components)}")
                shell_args = f"{shell_args} -c {' '.join(components)}"
            else:
                Log.info(f"Generating Bundle for All Cortex Components.")
                shell_args = f"{shell_args} -c all"
        if not components and not sos:
            Log.info("Generating Complete Support Bundle For SOS and Components Logs.")
            shell_args = f"{shell_args} -c all -s"
        # Get HostNames and Node Names.
        hostnames, node_list = await SupportBundle.fetch_host_from_salt()
        if not hostnames or not node_list:
            hostnames, node_list = await SupportBundle.fetch_host_from_cluster()
        if not isinstance(hostnames, list):
            return hostnames
        #GET SSH KEY for Root User
        ssh_key = os.path.expanduser(os.path.join("~", const.SSH_DIR, const.SSH_KEY))
        Log.debug(f"Current User > {current_user}, ssh key > {ssh_key}")
        # Start Daemon Threads for Starting SB Generation on all Nodes.
        for index, hostname in enumerate(hostnames):
            Log.debug(f"Connect to {hostname}")
            # Add Node Name to Shell Command
            shell_command = const.SUPPORT_BUNDLE_SHELL_COMMAND.format(
                args=shell_args, csm_path=const.CSM_PATH)
            thread_obj = Thread(SupportBundle.execute_ssh(hostname,
                                                          current_user, ssh_key,
                                                          shell_command, node_list[index]),
                                daemon=True)
            thread_obj.start()
        symlink_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                f"{const.SUPPORT_BUNDLE}.{const.SB_SYMLINK_PATH}")
        response_msg = (
            f"Please use the below ID for Checking the status of Support Bundle."
            f" \n{bundle_id}"
            f"\nPlease Find the file on -> {symlink_path} .\n")

        return Response(output=response_msg, rc=errors.CSM_OPERATION_SUCESSFUL)

    @staticmethod
    async def bundle_status(command):
        """
        Initializes the process for Displaying the Status for Support Bundle.
        :param command: Csm_cli Command Object :type: command
        :return: None
        """
        bundle_id = command.options.get("bundle_id")
        conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
        db = DataBaseProvider(conf)
        repo = SupportBundleRepository(db)
        all_nodes_status = await repo.retrieve_all(bundle_id)
        response = {"status": [each_status.to_primitive()
                               for each_status in all_nodes_status]}
        return Response(output=response, rc=errors.CSM_OPERATION_SUCESSFUL)

    @staticmethod
    async def fetch_ftp_data(ftp_details):
        """
        Fetch and Validate FTP Data.
        #todo: Need to Implement Validation Framework for CLI. And Inputs in it.
        :param ftp_details: Current Keys for FTP.
        :return:
        """
        Log.debug("Configuring FTP Channel for Support Bundle")
        ftp_details[const.HOST] = str(input("Input FTP Host: "))
        try:
            ftp_details[const.PORT] = int(input("Input FTP Port:  "))
        except ValueError:
            raise CsmError(errno.EINVAL, f"{const.PORT} must be a integer type.")
        ftp_details[const.USER] = str(input("Input FTP User: "))
        ftp_details[const.PASS] = str(input("Input FTP Password: "))
        ftp_details['remote_file'] = str(input("Input FTP Remote File Path: "))
        return ftp_details

    @staticmethod
    async def configure(command):
        """
        Configure FTP for Support Bundle
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        csm_conf_file_name = os.path.join(const.CSM_CONF_PATH,
                                          const.CSM_CONF_FILE_NAME)
        if not os.path.exists(csm_conf_file_name):
            raise CsmError(rc=errno.ENOENT, output="Config file is not exist")
        conf_file_data = Yaml(csm_conf_file_name).load()
        ftp_details = conf_file_data.get(const.SUPPORT_BUNDLE)
        ftp_details = await SupportBundle.fetch_ftp_data(ftp_details)
        conf_file_data[const.SUPPORT_BUNDLE] = ftp_details
        Yaml(csm_conf_file_name).dump(conf_file_data)
        hostnames, node_list = await SupportBundle.fetch_host_from_salt()
        if not hostnames or not node_list:
            hostnames, node_list = await SupportBundle.fetch_host_from_cluster()
        if not isinstance(hostnames, list):
            return hostnames
        for hostname in hostnames:
            process = SimpleProcess(
                f"scp {csm_conf_file_name}  {hostname}:{csm_conf_file_name}")
            stdout, stderr, rc = process.run()

    @staticmethod
    async def show_config(command):
        """
        Display Config for Current FTP.
        # Todo: Need to change this command to display the FTP Configuration
        # for individual node.
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        support_bundle_config = Conf.get(const.CSM_GLOBAL_INDEX,
                                         const.SUPPORT_BUNDLE)
        return Response(output=support_bundle_config, rc=CSM_OPERATION_SUCESSFUL)
