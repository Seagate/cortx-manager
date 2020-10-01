# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import sys
import os
import string
import random
import errno
from importlib import import_module
from csm.common.payload import Yaml, JsonMessage
from csm.core.blogic import const
from csm.core.services.support_bundle import SupportBundleRepository
from csm.common.errors import (CSM_OPERATION_SUCESSFUL, CsmError,
                            InvalidRequest, CSM_ERR_INVALID_VALUE)
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from csm.core.providers.providers import Response
from csm.common.conf import Conf
from cortx.utils.log import Log
import time
from csm.common.process import SimpleProcess

class SupportBundle:
    """
    This Class initializes the Support Bundle Generation for CORTX.
    """

    @staticmethod
    def import_provisioner_plugin():
        """Import Plugin for Provisioner."""
        try:
            params = {"username": const.NON_ROOT_USER,
                      "password": const.NON_ROOT_USER_PASS}
            provisioner = import_module(
                f"csm.plugins.{const.PLUGIN_DIR}.{const.PROVISIONER_PLUGIN}").ProvisionerPlugin(
                **params)
        except ImportError as e:
            Log.error(f"Provisioner package not installed on system. {e}")
            return None
        return provisioner

    @staticmethod
    async def fetch_host_from_salt():
        """
        This method fetch hostname for all nodes from Salt DB
        :return: hostnames : List of Hostname :type: List
        :return: node_list : : List of Node Name :type: List
        """
        process = SimpleProcess(
            "salt-call pillar.get cluster:node_list --out=json")
        _out, _err, _rc = process.run()
        if _rc != 0:
            Log.warn(f"Salt command failed : {_err}")
            return None, None
        output = JsonMessage(_out.strip()).load()
        nodes = output.get("local", [])
        hostnames = []
        for each_node in nodes:
            process = SimpleProcess(
                f"salt-call pillar.get cluster:{each_node}:hostname --out=json")
            _out, _err, _rc = process.run()
            if _rc != 0:
                Log.warn(f"Salt command failed : {_err}")
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
                            rc=CSM_ERR_INVALID_VALUE), None
        hostnames = []
        for each_node in active_nodes:
            hostnames.append(cluster_info.get(each_node, {}).get("hostname"))
        return hostnames, active_nodes

    @staticmethod
    def generate_bundle_id():
        """Generate Unique Bundle ID."""
        alphabet = string.ascii_lowercase + string.digits
        return f"SB{''.join(random.choices(alphabet, k = 8))}"

    @staticmethod
    def get_components(components):
        """Get Components to Generate Support Bundle."""
        if components and "all" not in components:
            Log.info(f"Generating bundle for  {' '.join(components)}")
            shell_args = f"{' '.join(components)}"
        else:
            Log.info("Generating bundle for all CORTX components.")
            shell_args = "all"
        return f" -c {shell_args}"

    @staticmethod
    async def bundle_generate(command) -> sys.stdout:
        """
        Initializes the process for Generating Support Bundle on Each CORTX Node.
        :param command: Csm_cli Command Object :type: command
        :return: None.
        """
        bundle_id = SupportBundle.generate_bundle_id()
        provisioner = SupportBundle.import_provisioner_plugin()
        if not provisioner:
            return Response(output = "Provisioner package not found.",
                            rc = str(errno.ENOENT))
        # Get Arguments From Command
        comment = command.options.get(const.SB_COMMENT)
        components = command.options.get(const.SB_COMPONENTS)
        if not components:
            components = []
        if command.options.get(const.SOS_COMP, False) == "true":
            components.append("os")
        Log.debug(str(components))
        comp_list = SupportBundle.get_components(components)

        # Get HostNames and Node Names.
        hostnames, node_list = await SupportBundle.fetch_host_from_salt()
        if not hostnames or not node_list:
            hostnames, node_list = await SupportBundle.fetch_host_from_cluster()
        if not isinstance(hostnames, list):
            return hostnames

        # Start SB Generation on all Nodes.
        for index, hostname in enumerate(hostnames):
            Log.debug(f"Connect to {hostname}")
            try:
                await provisioner.begin_bundle_generation(
                    f"bundle_generate '{bundle_id}' '{comment}' "
                    f"'{hostname}' {comp_list}", node_list[index])
            except InvalidRequest:
                return Response(output = "Bundle generation failed.\nPlease "
                         "check CLI for details.", rc = str(errno.ENOENT))
            except Exception as e:
                Log.error(f"Provisioner API call failed : {e}")
                return Response(output = "Bundle Generation Failed.",
                                rc = str(errno.ENOENT))

        symlink_path = Conf.get(const.CSM_GLOBAL_INDEX,
                                f"{const.SUPPORT_BUNDLE}.{const.SB_SYMLINK_PATH}")
        display_string_len = len(bundle_id) + 4
        response_msg = (
            f"Please use the below bundle id for checking the status of support bundle."
            f"\n{'-' * display_string_len}"
            f"\n| {bundle_id} |"
            f"\n{'-' * display_string_len}"
            f"\nPlease Find the file on -> {symlink_path} .\n")

        return Response(output = response_msg,
                        rc =CSM_OPERATION_SUCESSFUL)

    @staticmethod
    async def bundle_status(command):
        """
        Initializes the process for Displaying the Status for Support Bundle.
        :param command: Csm_cli Command Object :type: command
        :return: None
        """
        bundle_id = command.options.get("bundle_id", "")
        conf = GeneralConfig(Yaml(const.DATABASE_CONF).load())
        db = DataBaseProvider(conf)
        repo = SupportBundleRepository(db)
        all_nodes_status = await repo.retrieve_all(bundle_id)
        response = {"status": [each_status.to_primitive() for each_status in
                               all_nodes_status]}
        return Response(output = response, rc = CSM_OPERATION_SUCESSFUL)

    @staticmethod
    async def fetch_ftp_data(ftp_details):
        """
        Fetch and Validate FTP Data.
        #todo: Need to Implement Validation Framework for CLI. And Inputs in it.
        :param ftp_details: Current Keys for FTP.
        :return:
        """
        Log.debug("Configuring FTP channel for support bundle")
        ftp_details[const.HOST] = str(input("Input FTP Host: "))
        try:
            ftp_details[const.PORT] = int(input("Input FTP Port:  "))
        except ValueError:
            raise CsmError(rc = errno.EINVAL,
                           desc = f"{const.PORT} must be a integer type.")
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
            raise CsmError(rc = errno.ENOENT,
                           desc = "Config file does not exist.")
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
            process.run()

    @staticmethod
    async def show_config(command):
        """
        Display Config for Current FTP.
        # Todo: Need to change this command to display the FTP configuration for an individual node.
        :param command: Csm_cli Command Object :type: command
        :return:
        """
        support_bundle_config = Conf.get(const.CSM_GLOBAL_INDEX,
                                         const.SUPPORT_BUNDLE)
        return Response(output = support_bundle_config,
                        rc = CSM_OPERATION_SUCESSFUL)
