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


class ApiRoutes:
    @staticmethod
    def add_websocket_routes(router, ws_handler):
        router.add_get("/ws", ws_handler)
