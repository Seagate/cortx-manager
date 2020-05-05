#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          onboarding.py
 Description:       Implementation of onboarding views

 Creation Date:     12/05/2019
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json
from marshmallow import Schema, fields, validate, validates
from marshmallow.exceptions import ValidationError
from eos.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.permission_names import Resource, Action
from csm.core.controllers.view import CsmView, CsmResponse, CsmAuth


class OnboardingStateSchema(Schema):
    phase = fields.Str(required=True)


@CsmView._app_routes.view("/api/v1/onboarding/state")
class OnboardingStateView(CsmView):

    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["onboarding_config_service"]

    async def _validate_request(self, schema):
        try:
            json = await self.request.json()
            body = schema().load(json, unknown='EXCLUDE')
            return body
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Missing request body")
        except ValidationError as e:
            raise InvalidRequest(message_args=f"Invalid request body: {e}")

    @CsmAuth.public
    async def get(self):
        Log.debug("Getting onboarding state")
        phase = await self._service.get_current_phase()
        response = { 'phase': phase }
        return CsmResponse(response)

    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def patch(self):
        Log.debug("Updating onboarding state")
        # TODO: Check if the user has onboarding permissions
        body = await self._validate_request(OnboardingStateSchema)
        await self._service.set_current_phase(body['phase'])
        return CsmResponse()
