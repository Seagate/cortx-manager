#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          usl.py
 Description:       Services for USL calls

 Creation Date:     10/21/2019
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from aiohttp import web, ClientSession
from random import SystemRandom
from typing import Any, Dict, List
from uuid import UUID
import asyncio
import time

from csm.common.log import Log
from csm.common.services import ApplicationService
from csm.core.blogic import const


class UslService(ApplicationService):
    """
    Implements USL service operations.
    """
    # FIXME improve token management
    _token: str
    _fake_system_serial_number: str

    def __init__(self) -> None:
        """
        Constructor.
        """
        self._token = ''
        self._fake_system_serial_number = 'EES%012d' % time.time()

    # TODO replace stub
    async def get_device_list(self) -> List[Dict[str, str]]:
        """
        Provides a list with all available devices.

        :return: A list with dictionaries, each containing information about a specific device.
        """
        return [
            {
                'name': 'a_name',
                'productID': 'a_product_id',
                'serialNumber': '000000000000',
                'type': 'Internal',
                'uuid': '00000000-0000-0000-0000-000000000000',
                'vendorID': 'a_vendor_id',
            },
        ]

    # TODO replace stub
    async def get_device_volumes_list(self, device_id: UUID) -> List[Dict[str, Any]]:
        """
        Provides a list of all volumes associated to a specific device.

        :param device_id: Device UUID
        :return: A list with dictionaries, each containing information about a specific volume.
        """
        return [
            {
                'deviceUuid': '00000000-0000-0000-0000-000000000000',
                'filesystem': 'a_filesystem',
                'size': 0,
                'used': 0,
                'uuid': '00000000-0000-0000-0000-000000000001',
            },
        ]

    # TODO replace stub
    async def post_device_volume_mount(self, device_id: UUID, volume_id: UUID) -> Dict[str, str]:
        """
        Attaches a volume associated to a specific device to a mount point.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :return: A dictionary containing the mount handle and the mount path.
        """
        return {
            'handle': 'handle',
            'mountPath': '/mnt',
        }

    # TODO replace stub
    async def post_device_volume_unmount(self, device_id: UUID, volume_id: UUID) -> str:
        """
        Detaches a volume associated to a specific device from its current mount point.

        The current implementation reflects the API specification but does nothing.

        :param device_id: Device UUID
        :param volume_id: Volume UUID
        :return: The volume's mount handle
        """
        return 'handle'

    async def register_device(self, url: str, pin: str) -> None:
        """
        Executes device registration sequence. Communicates with the UDS server in order to start
        registration and verify its status.

        :param url: Registration URL as provided by the UDX portal
        :param pin: Registration PIN as provided by the UDX portal
        """
        # TODO use a single client session object; manage life cycle correctly
        async with ClientSession() as session:
            endpoint_url = const.UDS_SERVER_URL + '/uds/v1/registration/RegisterDevice'
            params = {'url': url, 'regPin': pin, 'regToken': self._token}
            Log.info(f'Start device registration at {const.UDS_SERVER_URL}')
            async with session.put(endpoint_url, params=params) as response:
                if response.status != 201:
                    reason = 'Could not start device registration'
                    Log.error(f'{reason}---unexpected status code {response.status}')
                    raise web.HTTPInternalServerError(reason=reason)
            Log.info('Device registration in process---waiting for confirmation')
            timeout_limit = time.time() + 60
            while time.time() < timeout_limit:
                async with session.get(endpoint_url) as response:
                    if response.status == 200:
                        Log.info('Device registration successful')
                        return
                    elif response.status != 201:
                        reason = 'Device registration failed'
                        Log.error(f'{reason}---unexpected status code {response.status}')
                        raise web.HTTPInternalServerError(reason=reason)
                await asyncio.sleep(1)
            else:
                reason = 'Could not confirm device registration status'
                Log.error(reason)
                raise web.HTTPGatewayTimeout(reason=reason)

    # TODO replace stub
    async def get_registration_token(self) -> Dict[str, str]:
        """
        Generates a random registration token.

        :return: A 12-digit token.
        """
        self._token = ''.join(SystemRandom().sample('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 12))
        return {'registrationToken': self._token}

    # TODO replace stub
    async def get_system(self) -> Dict[str, str]:
        """
        Provides information about the system.

        :return: A dictionary containing system information.
        """
        return {
            'model': 'EES',
            'type': 'ees',
            'serialNumber': self._fake_system_serial_number,
            'friendlyName': 'EESFakeSystem',
            'firmwareVersion': '0.00',
        }

    # TODO replace stub
    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """
        Provides a list of all network interfaces in a system.

        :return: A list containing dictionaries, each containing information about a specific
            network interface.
        """
        return [
            {
                'name': 'tbd',
                'type': 'tbd',
                'macAddress': 'AA:BB:CC:DD:EE:FF',
                'isActive': True,
                'isLoopback': False,
                'ipv4': '127.0.0.1',
                'netmask': '255.0.0.0',
                'broadcast': '127.255.255.255',
                'gateway': '127.255.255.254',
                'ipv6': '::1',
                'link': 'tbd',
                'duplex': 'tbd',
                'speed': 0,
            }
        ]
