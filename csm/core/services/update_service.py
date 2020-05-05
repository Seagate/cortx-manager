#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          update_service.py
 Description:       Implementation provisiner update status service.

 Creation Date:     04/08/2020
 Author:            Udayan Yaragattikar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from csm.common.errors import CsmError, CsmInternalError, InvalidRequest
from csm.common.services import Service, ApplicationService
from eos.utils.log import Log
from csm.core.data.models.upgrade import UpdateStatusEntry
from csm.core.blogic import const

import os


class UpdateService(ApplicationService):

    def __init__(self, provisioner, update_repo):
        self._provisioner = provisioner
        self._update_repo = update_repo

    async def upload_package(self, package_ref, **kwargs):
        raise NotImplementedError

    async def start_update(self):
        raise NotImplementedError
    
    async def get_current_status(self):
        raise NotImplementedError

    @Log.trace_method(Log.DEBUG)
    async def _get_renewed_model(self, update_id):
        """
        Fetch the most up-to-date information about the most recent firmware and software update process.
        Queries the DB, then queries the Provisioner if needed.
        """
        model = await self._update_repo.get_current_model(update_id)
        if model and model.is_in_progress():
            try:
                result = await self._provisioner.get_provisioner_job_status(model.provisioner_id)
                model.apply_status_update(result)
                await self._update_repo.save_model(model)
            except:
                raise CsmInternalError(f'Failed to fetch the status of an ongoing update process')
        return model

    @Log.trace_method(Log.INFO)
    async def _get_current_status(self, update_id):
        """
        Fetch current state of firmware and hotfix update process.
        Synchronizes it with the Provisioner service if necessary.

        Returns {} if there is no information (e.g. because CSM has never been updated)
        Otherwise returns a dictionary that describes the process
        """
        model = await self._get_renewed_model(update_id)
        if not model:
            return {}

        return model.to_printable()


