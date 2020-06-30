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
from csm.common.errors import InvalidRequest
from csm.core.blogic import const
from csm.core.controllers.validators import ValidationErrorFormatter
from marshmallow import (Schema, fields, ValidationError)
from csm.common.permission_names import Resource, Action


class PostNodeReplaceSchema(Schema):
    resource_name = fields.Str(required=True)


@CsmView._app_routes.view("/api/v1/maintenance/replace_node")
class ReplaceNodeView(CsmView):
    def __init__(self, request):
        """
        Instantiate Replace Node Controller Class.
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

    @CsmAuth.permissions({Resource.NODE_REPLACEMENT: {Action.CREATE}})
    async def post(self):
        """
        Trigger Replace Node Feature For Node Id Provided.
        """
        Log.debug("Handling Node Replace Start Request.")
        body = await self.request.json()
        try:
            PostNodeReplaceSchema().load(body, unknown=const.MARSHMALLOW_EXCLUDE)
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        return  await self._service.begin_process(body.get(const.RESOURCE_NAME))
