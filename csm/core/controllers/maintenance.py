#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          maintenance.py
 Description:       maintenance REST Api

 Creation Date:     02/11/2020
 Author:            Ajay Paratmandali

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
from csm.core.controllers.validators import Enum, ValidationErrorFormatter, Server, PortValidator
from marshmallow import (Schema, fields, ValidationError)
from csm.common.permission_names import Resource, Action


class GetMaintenanceSchema(Schema):
    action = fields.Str(required=True, validate=[Enum([const.NODE_STATUS, const.REPLACE_NODE])])

class PostMaintenanceSchema(Schema):
    action_items = [const.SHUTDOWN, const.START, const.STOP, const.REPLACE_NODE]
    resource_name = fields.Str(required=True)
    action = fields.Str(required=True, validate=[Enum(action_items)])
    hostname = fields.Str(missing=True, required=False, validate=[Server()])
    ssh_port = fields.Int(missing=True, required=False, validate=[PortValidator()])

@CsmView._app_routes.view("/api/v1/maintenance/cluster/{action}")
class MaintenanceView(CsmView):
    def __init__(self, request):
        super(MaintenanceView, self).__init__(request)
        self._service = self.request.app[const.MAINTENANCE_SERVICE]

    @CsmAuth.permissions({Resource.SYSTEM: {Action.LIST}})
    async def get(self):
        """
        Fetch All the Node Current Status.
        """
        Log.debug("Handling maintenance request")
        action = self.request.match_info[const.ACTION]
        try:
            GetMaintenanceSchema().load({const.ACTION: action},
                                        unknown=const.MARSHMALLOW_EXCLUDE)
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        service_action = {
            const.REPLACE_NODE: self._service.check_node_replacement_status,
            const.NODE_STATUS: self._service.get_status
        }
        return await service_action[action]()

    @CsmAuth.permissions({Resource.SYSTEM: {Action.UPDATE}})
    async def post(self):
        """
        Process Service Requests for Cluster Shutdown or Node Start Stop.
        :return:
        """
        Log.debug("Handling maintenance request")
        action = self.request.match_info[const.ACTION]
        body = await self.request.json()
        body[const.ACTION] = action
        try:
            PostMaintenanceSchema().load(body,
                                         unknown=const.MARSHMALLOW_EXCLUDE)
        except ValidationError as e:
            raise InvalidRequest(f"{ValidationErrorFormatter.format(e)}")
        not_valid_node = await self._service.validate_node_id(body.get("resource_name"), body[const.ACTION])
        if not_valid_node:
            raise InvalidRequest(not_valid_node)
        service_action = {
            const.SHUTDOWN: self._service.shutdown,
            const.START: self._service.start,
            const.STOP: self._service.stop,
            const.REPLACE_NODE: self._service.begin_process
        }
        return await service_action[action](**body)
