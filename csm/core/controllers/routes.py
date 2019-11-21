#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          routes.py
 Description:       adding route to web application

 Creation Date:     10/16/2019
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
# To add new route import from view file
from .view import CsmView
from .stats import StatsView
from .system_config import SystemConfigView
from csm.core.data.storage.system_config import SystemConfigStorage
from csm.core.blogic.storage import SyncInMemoryKeyValueStorage
from csm.core.controllers.s3_iam_users import IamUserView,  IamUserListView


class CsmRoutes():
    """
    Common class for adding routes
    """

    @staticmethod
    def add_routes(app):
        """
        Add routes to Web application
        """
        #TODO Following lines will be removed once integrated with DB
        system_config_storage = SystemConfigStorage(SyncInMemoryKeyValueStorage())
        app["system_config_storage"] = system_config_storage

        app.add_routes(CsmView._app_routes)



