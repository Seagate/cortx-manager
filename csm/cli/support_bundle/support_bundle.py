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
import errno
from threading import Thread
from csm.common.payload import Yaml
from csm.core.blogic import const
from csm.common.comm import SSHChannel
from csm.core.services.support_bundle import SupportBundleRepository
from csm.core.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.core.providers.providers import  Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.errors import CsmError
from csm.core.providers.providers import Response
from csm.common import errors
from csm.common.conf import Conf

class SupportBundle:
    """
    This Class initializes the Support Bundle Generation for EOS.
    """
    @staticmethod
    def execute_ssh(ip_address: str, bundle_id: str, comment: str,
                    node_name: str):
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
        :return:
        """
        try:
            ssh_conn_object = SSHChannel(ip_address, user=const.SSH_USER_NAME)
            ssh_conn_object.connect()
            bundle_generate = (f"csmcli bundle_generate '{bundle_id}' '{comment}' "
                               f"'{node_name}'")
            rc, output = ssh_conn_object.execute(bundle_generate)
            ssh_conn_object.disconnect()
        except CsmError:
            sys.stderr.write(f"Could Not Connect to {node_name}\n")

    @staticmethod
    async def bundle_generate(command) -> sys.stdout:
        """
        Initializes the process for Generating Support Bundle on Each EOS Node.
        :param command: Csm_cli Command Object :type: command
        :return: None
        """
        alphabet = string.ascii_lowercase + string.digits
        bundle_id = f"SB{''.join(random.choices(alphabet, k=8))}"
        comment = command.options.get("comment")
        cluster_file_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                          "SUPPORT_BUNDLE.cluster_file_path")
        if not cluster_file_path or not os.path.exists(cluster_file_path):
            repsonse_msg = {"error": (f"{cluster_file_path} not Found. \n"
            f"Please check if cluster info file is correctly configured.")}
            return Response(rc=errno.ENOENT, output=repsonse_msg)
        cluster_info = Yaml(cluster_file_path).load().get("cluster", {})
        active_nodes = cluster_info.get("node_list", [])
        if not active_nodes:
            response_msg = {"error":"No active nodes found. Cluster file may not be valid"}
            return Response(output=response_msg, rc=errors.CSM_ERR_INVALID_VALUE)
        threads = []
        try:
            for each_node in active_nodes:
                network = cluster_info.get(each_node, {}).get("network", {})
                ip_address = network.get("mgmt_nw", {}).get("ipaddr", )
                thread_obj = Thread(SupportBundle.execute_ssh(ip_address,
                                                              bundle_id, comment,
                                                              each_node))
                thread_obj.start()
                threads.append(thread_obj)

            response_msg = (f"Support Bundle Generation Started.\n"
                          f"Please use the below ID for Checking the status of "
                          f"Support Bundle. \n {bundle_id}\n")

            return Response(output=response_msg, rc=errors.CSM_OPERATION_SUCESSFUL)
        finally:
            for each_thread in threads:
                each_thread.join(timeout=600)

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
