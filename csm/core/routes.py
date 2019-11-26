#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          routes.py
 Description:       A file for AIOHTTP routes

 Creation Date:     09/05/2019
 Author:            Prathamesh Rodi
                    Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
# Last route is for debugging purposes only. Please see the description of the
# process_dbg_static_page() method.

from aiohttp import web
from csm.core.controllers import AlertsHttpController, UslController


class ApiRoutes:
    @staticmethod
    def add_rest_api_routes(
        router: web.UrlDispatcher,
        alerts_ctrl: AlertsHttpController,
        usl_ctrl: UslController
    ) -> None:
        # todo: Will be restructuring this part on Tuesday Morning.
        # self._app.router.add_view("/csm", CsmCliView),
        # self._app.web.get("/ws", self.process_websocket),
        router.add_view("/api/v1/alerts", alerts_ctrl.get_list_view_class()),
        router.add_view("/api/v1/alerts/{alert_id}", alerts_ctrl.get_view_class()),
        # self._app.router.add_view('/{path:.*}', self.process_dbg_static_page)
        router.add_view("/usl/v1/devices", usl_ctrl.get_device_view_class())
        router.add_view("/usl/v1/devices/{device_id}/volumes",
                        usl_ctrl.get_device_volumes_list_view_class())
        router.add_view("/usl/v1/devices/{device_id}/volumes/{volume_id}/mount",
                        usl_ctrl.get_device_volume_mount_view_class())
        router.add_view("/usl/v1/devices/{device_id}/volumes/{volume_id}/umount",
                        usl_ctrl.get_device_volume_unmount_view_class())
        # router.add_view("/usl/v1/events", usl_ctrl.get_events_view_class())
        router.add_view("/usl/v1/system", usl_ctrl.get_system_view_class())
        router.add_view("/usl/v1/system/network/interfaces",
                        usl_ctrl.get_network_interfaces_view_class())
        # router.add_view("/usl/v1/system/network/mounts",
        #                  usl_ctrl.get_network_mounts_list_view_class())
        # router.add_view("/usl/v1/system/network/mounts/{mount_id}",
        #                 usl_ctrl.get_network_mount_view_class())
        # router.add_view("/usl/v1/system/network/shares",
        #                  usl_ctrl.get_network_shares_list_view_class())
        # router.add_view("/usl/v1/system/network/shares/{share_id}",
        #                  usl_ctrl.get_network_share_view_class())
        # router.add_view("/system/preCheckAction",
        #                  usl_ctrl.get_precheck_action_view_class())
        router.add_view("/usl/v1/registrationToken",
                        usl_ctrl.get_registration_token_view_class())

    @staticmethod
    def add_websocket_routes(router, ws_handler):
        router.add_get("/ws", ws_handler)
