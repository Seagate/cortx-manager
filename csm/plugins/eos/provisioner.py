#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          provisioner.py
 Description:       Contains the implementation of Provisioner plugin.

 Creation Date:     02/25/2020
 Author:            Udayan Yaragattikar, Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio
import datetime
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from eos.utils.log import Log
from csm.core.blogic import const
from csm.common.errors import InvalidRequest, CsmInternalError
from csm.core.data.models.upgrade import (PackageInformation, ProvisionerStatusResponse,
                                          ProvisionerCommandStatus)
from csm.core.blogic.const import PILLAR_GET
import provisioner
import provisioner.freeze


class PackageValidationError(InvalidRequest):
    pass

class NetworkConfigFetchError(InvalidRequest):
    pass

class ClusterIdFetchError(InvalidRequest):
    pass

class CreateCsmUserError(InvalidRequest):
    pass

class ProductVersionFetchError(InvalidRequest):
    pass

class NodeIdFetchError(InvalidRequest):
    pass

# TODO: create a separate module for provisioner-related models
NetworkConfiguirationResponse = namedtuple('NetworkConfiguirationResponse', 'mgmt_vip cluster_ip')


class ProvisionerPlugin:
    """
    Plugin that provides provisioner's api integration.
    """

    PRVSNR_NETWORK_PARAM_VIP = 'network/mgmt_vip'
    PRVSNR_NETWORK_PARAM_CIP = 'network/cluster_ip'

    def __init__(self, username=None, password=None):
        try:
            self.provisioner = provisioner
            Log.info("Provisioner plugin is loaded")

            if username and password:
                self.provisioner.auth_init(
                    username=username,
                    password=password,
                    eauth="pam"
                )
        except Exception as error:
            self.provisioner = None
            Log.error(f"Provisioner module not found : {error}")

    async def _await_nonasync(self, func):
        pool = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(pool, func)

    @Log.trace_method(Log.DEBUG)
    async def validate_hotfix_package(self, path) -> PackageInformation:
        """
        Validate an update image
        :param path: Path to the image file
        :returns: a PackageInformation object
        :raises: PackageValidationError in case of an invalid package
        """
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                # The version argument has no effect here, but we need to pass it anyway
                version = self._generate_random_version()
                self.provisioner.set_eosupdate_repo(version, path, dry_run=True)
            except self.provisioner.errors.ProvisionerError as e:
                raise PackageValidationError(f"Package validation failed: {e}")

        await self._await_nonasync(_command_handler)

        # TODO: fix it once it is ready on the provisioner side
        validation_result = PackageInformation()
        validation_result.version = 'uknown_ver'
        validation_result.description = 'unknown_desc'
        return validation_result

    @Log.trace_method(Log.DEBUG)
    async def trigger_software_update(self, path):
        """
        Starts the software update.
        :param path: Path to a file that contains the update image
        :returns: Value which will later be used to poll for the status of the process
        """

        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                # Generating the version here as at the moment we cannot infer it from the package
                version = self._generate_random_version()
                self.provisioner.set_eosupdate_repo(version, path)
                return self.provisioner.eos_update(nowait=True)
            except Exception as e:
                Log.exception(e)
                raise CsmInternalError('Failed to start the software update process')
        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def get_provisioner_job_status(self, query_id: str) -> ProvisionerStatusResponse:
        """
        Polls Provisioner for the status of a software and firmware update process
        """
        def _command_handler():
            # TODO: separately handle the case when the problem is related to the communication to the provisioner
            try:
                self.provisioner.get_result(query_id)
                return ProvisionerStatusResponse(ProvisionerCommandStatus.Success)
            except self.provisioner.errors.PrvsnrCmdNotFinishedError as not_finished_err:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.InProgress, str(not_finished_err))
            except self.provisioner.errors.PrvsnrCmdNotFoundError as not_found_err:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.NotFound, str(not_found_err))
            except self.provisioner.errors.SaltCmdResultError as res_err:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.Failure, str(res_err))
            except self.provisioner.errors.ProvisionerError as pe:
                return ProvisionerStatusResponse(ProvisionerCommandStatus.Failure, str(pe))

        return await self._await_nonasync(_command_handler)


    def _generate_random_version(self):
        return datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")

    async def validate_package(self, file_path):
        # TODO: Provisioner api to validate package tobe implented here
        Log.debug(f"Validating package: f{file_path}")
        return {"version": "1.2.3",
                "file_path": file_path}

    async def trigger_firmware_update(self, fw_package_path):
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                return self.provisioner.fw_update(source = fw_package_path, nowait = True)
            except Exception as e:
                Log.exception(e)
                raise CsmInternalError('Failed to start the firmware update process.')

        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def set_ntp(self, ntp_data: dict):
        """
        Set ntp configuration using provisioner api.
        :param ntp_data: Ntp config dict
        :returns:
        """
        # TODO: Exception handling as per provisioner's api response
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                if (ntp_data.get(const.NTP_SERVER_ADDRESS, None) and
                        ntp_data.get(const.NTP_TIMEZONE_OFFSET, None)):
                    if self.provisioner:
                        Log.debug("Handling provisioner's set ntp api request")
                        self.provisioner.set_ntp(server=ntp_data[const.NTP_SERVER_ADDRESS],
                                    timezone=ntp_data[const.NTP_TIMEZONE_OFFSET].split()[-1])
            except self.provisioner.errors.ProvisionerError as error:
                Log.error(f"Provisioner api error : {error}")
                raise PackageValidationError(f"Provisioner package failed: {error}")

        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def create_system_user(self, username: str, password: str):
        """
        Create linux user using provisioner api.
        :param username: user name for system
        :param password: password for the system user
        :returns:
        """
        # TODO: Exception handling as per provisioner's api response
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                if ( username and password ):
                    Log.debug("Handling provisioner's create user api request")
                    self.provisioner.create_user(uname=username, passwd=password)
            except self.provisioner.errors.ProvisionerError as error:
                Log.error(f"Provisioner api error : {error}")
                raise CreateCsmUserError(f"System user creation failed: {error}")

        return await self._await_nonasync(_command_handler)

    async def set_ssl_certs(self, source: str) -> str:
        """ Install uploaded certificates and replicate them between nodes.
        TODO:
        """
        # TODO: validate path
        # TODO: make it async if possible
        def _command_handler():
            try:
                return self.provisioner.set_ssl_certs(source=source, nowait=True)
            except Exception as e:
                raise CsmInternalError(f'Failed to install certificate during provisioner '
                                       f'`set_ssl_certs` call: {e}')

        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        return await self._await_nonasync(_command_handler)

    async def get_provisioner_status(self, status_type):
        # TODO: Provisioner api to get status tobe implented here
        Log.debug(f"Getting provisioner status for : {status_type}")
        return {"status": "Successful"}

    @Log.trace_method(Log.DEBUG)
    async def get_network_configuration(self):
        """
        Queries the current network configration from the provisioner
        At the moment only queries VIP and CIP, later the method can be extended to fetch
        additional information

        :returns: an instance of NetworkConfiguirationResponse
        :raises: a CsmInternalError in case of query failure
        """
        if not self.provisioner:
            raise NetworkConfigFetchError("Provisioner is not instantiated")

        def _command_handler():
            try:
                response = self.provisioner.get_params(self.PRVSNR_NETWORK_PARAM_VIP, self.PRVSNR_NETWORK_PARAM_CIP)
                # The IPs are same for each node, so we can take any of them
                for node, params in response.items():
                    return NetworkConfiguirationResponse(
                        mgmt_vip=params[self.PRVSNR_NETWORK_PARAM_VIP],
                        cluster_ip=params[self.PRVSNR_NETWORK_PARAM_CIP]
                    )
            except Exception as error:
                Log.error(f"Provisioner api error : {error}")
                raise NetworkConfigFetchError(f"Network configuration fetching failed: {error}")

        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def get_cluster_id(self):
        if not self.provisioner:
            raise ClusterIdFetchError("Provisioner is not instantiated")

        def _command_handler():
            try:
                cluster_id = self.provisioner.get_cluster_id()
                return cluster_id
            except Exception as error:
                Log.error(f"Provisioner api error : {error}")
                raise ClusterIdFetchError(f"IDs fetching failed: {error}")

        return await self._await_nonasync(_command_handler)

    def get_dict(self, dictionary, keys, default=None):
        """
        Retrive value from nested dict.
        :param dictionary: Input dictionary
        :param keys: Tuple having keys in ordered format to find its value
        :returns: Value of given key otherwise return default value
        """
        for key in keys:
            if isinstance(dictionary, dict) and key in dictionary:
                dictionary = dictionary.get(key)
            else:
                return default
        return dictionary

    @Log.trace_method(Log.DEBUG)
    async def set_network(self, network_data: dict, config_type):
        """
        Set network configuration using provisioner api.
        :param network_data: Nerwork config dict
        :returns:
        """
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                mgmt_nodes = data_nodes = dns_nodes = []
                data_network_config = {}
                if network_data.get(const.MANAGEMENT_NETWORK):
                    mgmt_nodes = self.get_dict(network_data, (
                        const.MANAGEMENT_NETWORK, const.IPV4, const.NODES), default=[])
                if network_data.get(const.DATA_NETWORK):
                    data_network_config = self.get_dict(network_data, (
                        const.DATA_NETWORK, const.IPV4), default={})
                    data_nodes = data_network_config.get(const.NODES, [])
                if network_data.get(const.DNS_NETWORK):
                    dns_nodes = self.get_dict(network_data, (
                        const.DNS_NETWORK, const.NODES), default=[])
                
                mgmt_vip_address = cluster_ip_address = primary_data_ip_address = None
                primary_data_netmask_address = secondary_data_netmask_address = None
                secondary_data_ip_address = dns_servers_list = search_domains_list = None
                data_nw_dhcp = data_network_config.get(const.IS_DHCP, None)
                primary_data_gateway_address = secondary_data_gateway_address = None
                
                for node in mgmt_nodes:
                    if node[const.NAME] == const.VIP_NODE:
                        mgmt_vip_address = node.get(const.IP_ADDRESS, None)
                for node in data_nodes:
                    if node[const.NAME] == const.VIP_NODE:
                        cluster_ip_address = node.get(const.IP_ADDRESS, None)
                    if node[const.NAME] == const.PRIMARY_NODE:
                        primary_data_ip_address = node.get(const.IP_ADDRESS, None)
                        primary_data_netmask_address = node.get(const.NETMASK, None)
                        primary_data_gateway_address = node.get(const.GATEWAY, None)
                    if node[const.NAME] == const.SECONDARY_NODE:
                        secondary_data_ip_address = node.get(const.IP_ADDRESS, None)
                        secondary_data_netmask_address = node.get(const.NETMASK, None)
                        secondary_data_gateway_address = node.get(const.GATEWAY, None)
                for node in dns_nodes:
                    if node[const.NAME] == const.PRIMARY_NODE:
                        dns_servers_list = node.get(const.DNS_SERVER, None)
                        search_domains_list = node.get(const.SEARCH_DOMAIN, None)

                Log.debug("Handling provisioner's set network api request")
                if config_type == const.SYSTEM_CONFIG:
                    if data_nw_dhcp:
                        self.provisioner.set_network(mgmt_vip=mgmt_vip_address,
                                cluster_ip=cluster_ip_address,
                                primary_data_ip=self.provisioner.UNDEFINED,
                                primary_data_netmask=self.provisioner.UNDEFINED,
                                primary_data_gateway=self.provisioner.UNDEFINED,
                                secondary_data_ip=self.provisioner.UNDEFINED,
                                secondary_data_netmask=self.provisioner.UNDEFINED,
                                secondary_data_gateway=self.provisioner.UNDEFINED,
                                dns_servers=dns_servers_list,
                                search_domains=search_domains_list)
                    else:
                        self.provisioner.set_network(mgmt_vip=mgmt_vip_address,
                                cluster_ip=cluster_ip_address,
                                primary_data_ip=primary_data_ip_address,
                                primary_data_netmask=primary_data_netmask_address,
                                primary_data_gateway=primary_data_gateway_address,
                                secondary_data_ip=secondary_data_ip_address,
                                secondary_data_netmask=secondary_data_netmask_address,
                                secondary_data_gateway=secondary_data_gateway_address,
                                dns_servers=dns_servers_list,
                                search_domains=search_domains_list)
                if config_type == const.MANAGEMENT_NETWORK:
                    self.provisioner.set_network(mgmt_vip=mgmt_vip_address)
                if config_type == const.DATA_NETWORK:
                    if data_nw_dhcp:
                        self.provisioner.set_network(cluster_ip=cluster_ip_address,
                                primary_data_ip=self.provisioner.UNDEFINED,
                                primary_data_netmask=self.provisioner.UNDEFINED,
                                primary_data_gateway=self.provisioner.UNDEFINED,
                                secondary_data_ip=self.provisioner.UNDEFINED,
                                secondary_data_netmask=self.provisioner.UNDEFINED,
                                secondary_data_gateway=self.provisioner.UNDEFINED)
                    else:
                        self.provisioner.set_network(cluster_ip=cluster_ip_address,
                                primary_data_ip=primary_data_ip_address,
                                primary_data_netmask=primary_data_netmask_address,
                                primary_data_gateway=primary_data_gateway_address,
                                secondary_data_ip=secondary_data_ip_address,
                                secondary_data_netmask=secondary_data_netmask_address,
                                secondary_data_gateway=secondary_data_gateway_address)
                if config_type == const.DNS_NETWORK:
                    self.provisioner.set_network(dns_servers=dns_servers_list,
                                search_domains=search_domains_list)
            except self.provisioner.errors.ProvisionerError as e:
                Log.error(f"Provisioner api error : {e}")
                raise PackageValidationError(f"Provisioner package failed: {e}")

        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def get_current_version(self):
        """
        Fetch product version information from provisioner
        :returns: Dict having installed product version
        """
        if not self.provisioner:
            raise PackageValidationError("Provisioner is not instantiated")

        def _command_handler():
            try:
                # TODO: Provisioner api integration and error handling as per api response.
                return {"NAME": "EES",
                        "VERSION": "1.0.0",
                        "BUILD": "193",
                        "RELEASE": "Cortx-1.0.0-12-rc7",
                        "OS": "Red Hat Enterprise Linux Server release 7.7 (Maipo)",
                        "DATETIME": "09-Jun-2020 05:57 UTC",
                        "KERNEL": "3.10.0_1062.el7",
                        "LUSTRE_VERSION": ""
                        }
            except self.provisioner.errors.ProvisionerError as error:
                Log.error(f"Provisioner api error : {error}")
                raise ProductVersionFetchError(f"Product version fetching failed: {error}")

        return await self._await_nonasync(_command_handler)

    @Log.trace_method(Log.DEBUG)
    async def start_node_replacement(self, node_id):
        """
        Begin Node Replacement Prodecure.
        :param: node_id: Node Name :type: String
        :return: Job ID for Node Replacement
        """
        # todo: Will be Implementing this once received the integration setps from Provisioner.
        return "1234"

    @Log.trace_method(Log.DEBUG)
    async def get_node_id(self):
        if not self.provisioner:
            raise NodeIdFetchError("Provisioner is not instantiated")

        def _command_handler():
            try:
                node_id_info = self.provisioner.get_node_id()
                return node_id_info
            except Exception as error:
                Log.error(f"Node IDs fetching failed : {error}")
                raise NodeIdFetchError(f"Node IDs fetching failed: {error}")

        return await self._await_nonasync(_command_handler)