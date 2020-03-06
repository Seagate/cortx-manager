#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       Services for SystemConfigSettings handling

 Creation Date:     10/10/2019
 Author:            Soniya Moholkar, Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from typing import List

from csm.common.errors import CsmNotFoundError
from csm.common.email import EmailSender, EmailError
from csm.common.queries import SortBy
from csm.common.services import ApplicationService
from csm.common.template import Template
from csm.core.blogic import const
from eos.utils.db import Query
from eos.utils.db.filters import Compare
from csm.core.data.db.db_provider import (DataBaseProvider)
from csm.common.log import Log
from csm.core.data.models.system_config import (SystemConfigSettings, 
                                                EmailConfig, OnboardingLicense)

SYSTEM_CONFIG_NOT_FOUND = "system_config_not_found"

class SystemConfigManager:
    """
    The class encapsulates system config management activities.
    """

    def __init__(self, storage: DataBaseProvider) -> None:
        self.storage = storage

    async def create(self,
                     system_config: SystemConfigSettings) -> SystemConfigSettings:
        """
        Stores a new system config
        :param system_config: System config settings model instance
        :returns: System config settings object.
        """
        # TODO Model Validation.
        return await self.storage(SystemConfigSettings).store(system_config)

    async def get_system_config_by_id(self,
                                      config_id: str) -> SystemConfigSettings:
        """
        Fetches system config based on id
        :param config_id: System config identifier
        :returns: System config settings object in case of success. None otherwise.
        """
        query = Query().filter_by(Compare(SystemConfigSettings.config_id, '=',
                                          config_id))
        return next(iter(await self.storage(SystemConfigSettings).get(query)),
                    None)

    async def get_system_config_list(self, offset: int = None, limit: int = None,
                                     sort: SortBy = None) -> List[SystemConfigSettings]:
        """
        Fetches the list of system config.
        :param offset: Number of items to skip.
        :param limit: Maximum number of items to return.
        :param sort: What field to sort on.
        :returns: A list of System Config models
        """
        query = Query()

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        if sort:
            query = query.order_by(getattr(SystemConfigSettings, sort.field),
                                   sort.order)
        Log.debug(f"Get system config list query:{query}")
        return await self.storage(SystemConfigSettings).get(query)

    async def count(self):
        return await self.storage(SystemConfigSettings).count(None)

    async def save(self, system_config: SystemConfigSettings):
        """
        Stores an already existing System config.
        :param system_config: System config settings model instance
        """
        # TODO: validate the model
        Log.debug("Save system config")
        await self.storage(SystemConfigSettings).store(system_config)

    async def delete(self, config_id: str) -> None:
        """
        Delete system config based on id
        :param config_id: System config identifier
        """
        Log.debug(f"Delete system config. Config_id:{config_id}")
        await self.storage(SystemConfigSettings).delete(
            Compare(SystemConfigSettings.config_id, \
                    '=', config_id))

    async def get_current_config(self):
        # TODO: give it more thought
        config_list = await self.get_system_config_list(limit=1)
        return next(iter(config_list)) if config_list else None
    
    async def create_license(self,
                     license: OnboardingLicense) -> OnboardingLicense:
        """
        Stores a new onboarding license key
        :param license: Onboarding license model instance
        :returns: Onboarding license object.
        """
        return await self.storage(OnboardingLicense).store(license)


class SystemConfigAppService(ApplicationService):
    """
    Service that exposes system config management actions.
    """

    def __init__(self, provisioner, system_config_mgr: SystemConfigManager, 
                 email_test_template=None):
        self.system_config_mgr = system_config_mgr
        self.email_test_template = email_test_template
        self._provisioner = provisioner

    async def create_system_config(self, config_id: str, **kwargs) -> dict:
        """
        Handles the system config creation
        :param config_id: system Config identifier
        :returns: A dictionary describing the newly created system config.
        """
        # TODO Validation
        system_config = SystemConfigSettings.instantiate_system_config(config_id)
        await system_config.update(kwargs)
        await self.system_config_mgr.create(system_config)
        return system_config.to_primitive()

    async def get_system_config_list(self):
        """
        Fetches the list of system config
        :returns: A list of System Config
        """
        system_config_list = await self.system_config_mgr.get_system_config_list()
        if not system_config_list:
            system_config_list = []
        return [system_config.to_primitive() for system_config in
                system_config_list]

    async def get_system_config_by_id(self, config_id: str):
        """
        Fetches a system config based on id
        :param config_id: System config identifier
        :returns: A dict of system config
        """
        system_config = await self.system_config_mgr.get_system_config_by_id(
            config_id)
        if not system_config:
            raise CsmNotFoundError("There is no such system config",
                                   SYSTEM_CONFIG_NOT_FOUND)
        return system_config.to_primitive()

    async def update_system_config(self, config_id: str,
                                   new_values: dict) -> dict:
        """
        Update a system config based on id
        :param config_id: System config identifier
        :returns: A dict of system config
        """
        system_config = await self.system_config_mgr.get_system_config_by_id(
            config_id)
        if not system_config:
            raise CsmNotFoundError("There is no such system config",
                                   SYSTEM_CONFIG_NOT_FOUND)

        await system_config.update(new_values)
        await self.system_config_mgr.save(system_config)
        # Calling provisioner's api to set ntp configuration
        if new_values.get(const.DATE_TIME_SETTING, {}).get(const.NTP, {}):
            ntp_data = new_values.get(const.DATE_TIME_SETTING, {}).get(const.NTP, {})
            await self._provisioner.set_ntp(ntp_data)
        
        return system_config.to_primitive()

    async def delete_system_config(self, config_id: str):
        """
        Delete system config based on id
        :param config_id: System config identifier
        :returns: An empty dict
        """
        system_config = await self.system_config_mgr.get_system_config_by_id(
            config_id)
        if not system_config:
            raise CsmNotFoundError("There is no such system config",
                                   SYSTEM_CONFIG_NOT_FOUND)
        await self.system_config_mgr.delete(config_id)
        return {}

    async def test_email_config(self, config_data: dict) -> bool:
        config = EmailConfig()
        config.update(config_data)

        smtp_config = config.to_smtp_config()
        smtp_config.timeout = const.CSM_SMTP_TEST_EMAIL_TIMEOUT
        smtp_config.reconnect_attempts = const.CSM_SMTP_TEST_EMAIL_ATTEMPTS

        target_emails = [x.strip() for x in config.email.split(',')]
        html_body = self.email_test_template.render()
        subject = const.CSM_SMTP_TEST_EMAIL_SUBJECT

        message = EmailSender.make_multipart(config.smtp_sender_email,
            config.email, subject, html_body)
        try:
            sender = EmailSender(smtp_config)
            success = await sender.send_message(message)
            if len(success) == 0:
                return {"status": True, "failed_recipients": []}
            else:
                return {"status": False, "error": "Some recipients did not receive the message",
                    "failed_recipients": success.keys()}
        except EmailError as e:
            return {"status": False, "error": str(e), "failed_recipients": target_emails}
    
    async def create_onboarding_license(self, 
                            csm_onboarding_license_key: str, **kwargs) -> dict:
        """
        Handles the onboarding license key store
        :param csm_onboarding_license_key: license key identifier
        :returns: A dict describing the newly created onboarding license key.
        """
        Log.debug(f"Create on boarding license key."
                  f"license_key: {csm_onboarding_license_key}")
        onboarding_license = OnboardingLicense(csm_onboarding_license_key)
        await onboarding_license.update(kwargs)
        await self.system_config_mgr.create_license(onboarding_license)
        return onboarding_license.to_primitive()

    async def get_provisioner_status(self, status_type):
        """
        Fetch provisioner config status for network config, sw_update.
        :param status_type: Input parameter like netwok, sw_update to 
        get provisioner status accordingly
        :returns: Provisioner's success or failed status
        """
        # Calling provisioner's api to get status
        return await self._provisioner.get_provisioner_status(status_type)
    

