#!/usr/bin/env python3
"""
 ****************************************************************************
 Filename:          node_replacement.py
 Description:       Node Replacement API

 Creation Date:     06/26/2020
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


from .view import CsmView, CsmAuth
from eos.utils.log import Log
from csm.core.blogic import const
from marshmallow import (Schema, fields)
from csm.common.permission_names import Resource, Action


class PostNodeReplaceSchema(Schema):
    resource_name = fields.Str(required=True)


@CsmView._app_routes.view("/api/v1/maintenance/replace_node")
class ReplaceNodeView(CsmView):
    def __init__(self, request):
        """
        Instantiate Replace Node Controller
        :param request:
        """
        super(ReplaceNodeView, self).__init__(request)
        self._service = self.request.app[const.REPLACE_NODE_SERVICE]

    @CsmAuth.permissions({Resource.NODE_REPLACEMENT: {Action.LIST}})
    async def get(self):
        """
                Trigger Replace Node Feature For Node Id Provided.
                """
        Log.debug("Checking Status of Node Replacement.")
        return await self._service.check_status()
