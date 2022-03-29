# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import json
import uuid

from typing import Dict

from csm.common.errors import InvalidRequest
from cortx.utils.log import Log
from marshmallow import Schema, fields, validate, validates
from marshmallow.exceptions import ValidationError

from .validators import Server, Ipv4, DomainName
from .view import CsmView, CsmResponse, CsmAuth
from csm.core.blogic import const
from csm.core.data.models.system_config import ApplianceName
from csm.common.permission_names import Resource, Action

# Marshmallow nested schema classes to form system configuration settings schema structure
class Ipv4NodesSchema(Schema):
    """
    Ipv4 nodes schema class for common fields in management network and
    data network settings.
    """
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    ip_address = fields.Str(validate=Ipv4(), required=True)
    hostname = fields.Str(allow_none=True)
    gateway = fields.Str(validate=Ipv4(), allow_none=True)
    netmask = fields.Str(validate=Ipv4(), allow_none=True)

class Ipv6NodesSchema(Schema):
    """
    Ipv6 nodes schema class for common fields in management network and
    data network settings.
    """
    id = fields.Int(allow_none=True)
    ip_address = fields.List(fields.Str(), allow_none=True)
    gateway = fields.Str(allow_none=True)
    address_label = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)

class Ipv4BaseSchema(Schema):
    """
    Ipv4 base schema class for common ipv4 setting in management network and
    data network settings.
    """
    is_dhcp = fields.Boolean(allow_none=True)
    nodes = fields.List(fields.Nested(Ipv4NodesSchema, allow_none=True,
                                      unknown='EXCLUDE'))

class ManagementNetworkIpv6Schema(Schema):
    """
    Management network ipv6 is nested schema class used to form management
    network settings schema.
    """
    is_dhcp = fields.Boolean(allow_none=True)
    ip_address = fields.List(fields.Str(), allow_none=True)
    gateway = fields.Str(allow_none=True)
    address_label = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)

class ManagementNetworkSettingsSchema(Schema):
    """
    Schema for management network settings grouped with nested schema classes like
    ipv4 base and management network ipv6.
    Management network settings schema class is used to form system config settings schema.
    """
    ipv4 = fields.Nested(Ipv4BaseSchema, allow_none=True, unknown='EXCLUDE')
    ipv6 = fields.Nested(ManagementNetworkIpv6Schema, allow_none=True,
                         unknown='EXCLUDE')

class DataNetworkSettingsIpv6Schema(Schema):
    """
    Data network ipv6 is nested schema class used to form data network settings schema.
    """
    is_auto = fields.Boolean(allow_none=True)
    nodes = fields.List(fields.Nested(Ipv6NodesSchema, allow_none=True,
                                      unknown='EXCLUDE'))

class DataNetworkSettingsSchema(Schema):
    """
    Schema for data network settings grouped with nested schema classes like ipv4 base and
    data network ipv6.
    Data network settings schema class is used to form system config settings schema.
    """
    is_external_load_balancer = fields.Boolean(allow_none=True)
    ipv4 = fields.Nested(Ipv4BaseSchema, allow_none=True, unknown='EXCLUDE')
    ipv6 = fields.Nested(DataNetworkSettingsIpv6Schema, allow_none=True,
                         unknown='EXCLUDE')

class DnsNetworkSettingsNodes(Schema):
    """
    Dns network setting nodes is nested schema class used to form dns network
    settings schema.
    """
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    dns_servers = fields.List(fields.Str(required=True))
    search_domain = fields.List(fields.Str(required=True))

class DnsNetworkSettingsSchema(Schema):
    """
    Schema for dns network settings grouped with nested schema classes like
    dns network setting nodes.
    Dns network settings schema class is used to form system config settings schema
    """
    nodes = fields.List(fields.Nested(DnsNetworkSettingsNodes,
                                      allow_none=True, unknown='EXCLUDE'))

class NtpSchema(Schema):
    """
    Ntp is nested schema class used to form date time settings schema.
    """
    ntp_server_address = fields.Str(required=True)
    ntp_timezone_offset = fields.Str(required=True)

class ManualDateTimeSchema(Schema):
    """
    Manual date time is nested schema class used to form date time settings schema.
    """
    date = fields.Str(allow_none=True)
    hour = fields.Str(allow_none=True)
    minute = fields.Str(allow_none=True)
    clock = fields.Str(allow_none=True)

class DateTimeSettingsSchema(Schema):
    """
    Schema for date time settings grouped with nested schema classes like ntp
    and manual date time.
    Date time settings schema class is used to form system config settings schema.
    """
    is_ntp = fields.Boolean(allow_none=True)
    ntp = fields.Nested(NtpSchema, allow_none=True, unknown='EXCLUDE')
    date_time = fields.Nested(ManualDateTimeSchema, allow_none=True,
                              unknown='EXCLUDE')

class EmailConfigSchema(Schema):
    """
    Email config is nested schema class used to form notification schema
    """
    smtp_server = fields.Str(validate=Server(), allow_none=True)
    smtp_port = fields.Int(validate=validate.Range(max=65535), allow_none=True)
    smtp_protocol = fields.Str(allow_none=True)
    smtp_sender_email = fields.Email(allow_none=True)
    smtp_sender_password = fields.Str(validate=validate.Length(min=4, max=64),
                                      allow_none=True)
    email = fields.Str(allow_none=True)

    @validates('smtp_protocol')
    def validate_smtp_protocol(self, value):
        return str(value).lower() in ['tls', 'ssl', 'starttls', 'none']


class SyslogConfigSchema(Schema):
    """
    Syslog config is nested schema class used to form notification schema
    """
    syslog_server = fields.Str(validate=Server(), allow_none=True)
    syslog_port = fields.Int(validate=validate.Range(max=65535), allow_none=True)

class NotificationSchema(Schema):
    """
    Schema for notification grouped with nested schema classes like email config
    and syslog config.
    Notification schema class is used to form system config settings schema
    """
    email = fields.Nested(EmailConfigSchema, allow_none=True, unknown='EXCLUDE')
    syslog = fields.Nested(SyslogConfigSchema, allow_none=True, unknown='EXCLUDE')

class LdapConfigSchema(Schema):
    """
    Ldap config is nested schema class used to form system config settings schema
    """
    user_search_base = fields.Str(validate=validate.Length(min=4, max=32),
                                  allow_none=True)
    server = fields.Str(validate=Server(), allow_none=True)
    port = fields.Int(validate=validate.Range(max=65535), allow_none=True)
    alt_server = fields.Str(validate=Server(), allow_none=True)
    alt_port = fields.Int(validate=validate.Range(max=65535), allow_none=True)

class SystemConfigSettingsSchema(Schema):
    """
    Schema for complete system config settings grouped with nested schema classes like
    management network, data network, dns network, date time, notification and ldap settings.
    """
    appliance_name = fields.Str(validate=validate.Regexp('^[A-Za-z0-9_-]{2,255}$'),
                                allow_none=True, unknown='EXCLUDE')
    management_network_settings = fields.Nested(ManagementNetworkSettingsSchema,
                                                allow_none=True, unknown='EXCLUDE')
    data_network_settings = fields.Nested(DataNetworkSettingsSchema,
                                          allow_none=True, unknown='EXCLUDE')
    dns_network_settings = fields.Nested(DnsNetworkSettingsSchema,
                                         allow_none=True, unknown='EXCLUDE')
    date_time_settings = fields.Nested(DateTimeSettingsSchema,
                                       allow_none=True,unknown='EXCLUDE')
    notifications = fields.Nested(NotificationSchema, allow_none=True,
                                  unknown='EXCLUDE')
    is_summary = fields.Boolean(allow_none=True)
    ldap = fields.Nested(LdapConfigSchema, allow_none=True,unknown='EXCLUDE')


class SystemConfigConverter:
    @staticmethod
    def _view_to_model(d: Dict) -> Dict:
        """
        Converts a dictionary representing a system config view into a dictionary representing a
        system config model, in place. Returns the modified dictionary as a convenience.

        :param d: Dictionary representing a system config view
        :returns: Modified input dictionary representing a system config model
        """
        appliance_name = d.get(const.APPLIANCE_NAME)
        if appliance_name is not None:
            d[const.APPLIANCE_NAME] = ApplianceName.instantiate(appliance_name).to_native()
        return d

    @staticmethod
    def _model_to_view(d: Dict) -> Dict:
        """
        Converts a dictionary representing a system config model into a dictionary representing a
        system config view, in place. Returns the modified dictionary as a convenience.

        :param d: Dictionary representing a system config model
        :returns: Modified input dictionary representing a system config view
        """
        if (isinstance(d[const.APPLIANCE_NAME], dict) and
            d[const.APPLIANCE_NAME].get(const.APPLIANCE_NAME) is not None
        ):
            d[const.APPLIANCE_NAME] =  d[const.APPLIANCE_NAME][const.APPLIANCE_NAME]
        return d


@CsmView._app_routes.view("/api/v1/sysconfig")
@CsmView._app_routes.view("/api/v2/sysconfig")
class SystemConfigListView(CsmView):

    _converter = SystemConfigConverter()

    """
    System Configuration related routes
    """

    def __init__(self, request):
        super(SystemConfigListView, self).__init__(request)
        self._service = self.request.app[const.SYSTEM_CONFIG_SERVICE]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching user config
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling system config fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")
        system_config_list = await self._service.get_system_config_list()
        for system_config in system_config_list:
            SystemConfigListView._converter._model_to_view(system_config)
        return system_config_list

    """
    POST REST implementation for creating a system config
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def post(self):
        Log.debug(f"Handling system config post request."
                  f" user_id: {self.request.session.credentials.user_id}")
        try:
            schema = SystemConfigSettingsSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        system_config = await self._service.create_system_config(
            str(uuid.uuid4()), **SystemConfigListView._converter._view_to_model(config_data))
        return SystemConfigListView._converter._model_to_view(system_config)

class ConfigTypeSchema(Schema):
    """
    Schema class for validate query string to update config accordingly  
    """
    config_type = fields.String(required=True, 
                           validate=validate.OneOf(const.SYSCONFIG_TYPE))

@CsmView._app_routes.view("/api/v1/sysconfig/{config_id}")
@CsmView._app_routes.view("/api/v2/sysconfig/{config_id}")
class SystemConfigView(CsmView):

    _converter = SystemConfigConverter()

    def __init__(self, request):
        super(SystemConfigView, self).__init__(request)
        self._service = self.request.app[const.SYSTEM_CONFIG_SERVICE]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching system config
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.LIST}})
    async def get(self):
        Log.debug(f"Handling system config fetch request."
                  f" user_id: {self.request.session.credentials.user_id}")

        id = self.request.match_info["config_id"]
        system_config = await self._service.get_system_config_by_id(id)
        return SystemConfigView._converter._model_to_view(system_config)

    """
    PUT REST implementation for creating a system config
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    @CsmView.asyncio_shield
    async def put(self):
        Log.debug(f"Handling system config put request."
                  f" user_id: {self.request.session.credentials.user_id}")

        try:
            id = self.request.match_info["config_id"]
            schema = SystemConfigSettingsSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        system_config = await self._service.update_system_config(
            id, SystemConfigView._converter._view_to_model(config_data))
        return SystemConfigView._converter._model_to_view(system_config)
    
    """
    PATCH REST implementation for updating a system config data
    based on config type
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    @CsmView.asyncio_shield
    async def patch(self):
        Log.debug(f"Handling system config patch request."
                  f" user_id: {self.request.session.credentials.user_id}")

        try:
            id = self.request.match_info["config_id"]
            config_type_schema = ConfigTypeSchema()
            system_config_schema = SystemConfigSettingsSchema()
            config_data = system_config_schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
            request_data = config_type_schema.load(self.request.rel_url.query, 
                                                   unknown='EXCLUDE')
        except json.decoder.JSONDecodeError as jde:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        config_type = request_data["config_type"]
        system_config = await self._service.update_system_config_by_type(
            config_type, id, SystemConfigView._converter._view_to_model(config_data))
        return SystemConfigView._converter._model_to_view(system_config)

@CsmView._app_routes.view("/api/v1/sysconfig_helpers/email_test")
@CsmView._app_routes.view("/api/v2/sysconfig_helpers/email_test")
class TestEmailView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SYSTEM_CONFIG_SERVICE]

    """
    POST REST implementation for sendting test emails
    """
    @CsmAuth.permissions({Resource.NOTIFICATION: {Action.UPDATE}})
    async def post(self):
        Log.debug("Handling system config email test request")

        try:
            schema = EmailConfigSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        return await self._service.test_email_config(config_data)

class OnboardingLicenseSchema(Schema):
    """
    Onboarding license schema class for validation
    """
    csm_onboarding_license_key = fields.Str(required=True)

@CsmView._app_routes.view("/api/v1/license/onboarding")
@CsmView._app_routes.view("/api/v2/license/onboarding")
@CsmAuth.public
class OnboardingLicenseView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SYSTEM_CONFIG_SERVICE]
        
    """
    POST REST implementation for onboarding license key 
    """
    @CsmAuth.permissions({Resource.MAINTENANCE: {Action.UPDATE}})
    async def post(self):
        Log.info("Handling onboarding license post request")

        try:
            schema = OnboardingLicenseSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(f"Invalid request body: {val_err}")
        response = await self._service.create_onboarding_license(**config_data)
        return CsmResponse(response)

class ProvisionerStatusSchema(Schema):
    """
    Schema class for validate query string to get provisioner status accordingly  
    """
    status_type = fields.String(required=True, 
                           validate=validate.OneOf(const.PROVISIONER_CONFIG_TYPES))

@CsmView._app_routes.view("/api/v1/provisioner/status")
@CsmView._app_routes.view("/api/v2/provisioner/status")
class ProvisionerStatus(CsmView):
    """
    Rest implementation to get provisioner config status like success or faield
    for network config, s/w update etc.
    """
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app[const.SYSTEM_CONFIG_SERVICE]
        
    """
    GET REST implementation for fetching provisioner status
    """
    @CsmAuth.permissions({Resource.AUDITLOG: {Action.LIST}})
    async def get(self):
        Log.debug("Handling provisioner status fetch request")
        provisioner_status = ProvisionerStatusSchema()
        try:
            request_data = provisioner_status.load(self.request.rel_url.query, 
                                                   unknown='EXCLUDE')
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid value for provisioner status", str(val_err))

        status_type = request_data["status_type"]
        return await self._service.get_provisioner_status(status_type)
