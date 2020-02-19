#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       controllers for system config settings

 Creation Date:     10/14/2019
 Author:            Soniya Moholkar, Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json
import uuid

from csm.common.errors import InvalidRequest
from csm.common.log import Log
from marshmallow import Schema, fields, validate
from marshmallow.exceptions import ValidationError

from .validators import Server, Ipv4, DomainName
from .view import CsmView

# Marshmallow nested schema classes to form system configuration settings schema structure
class Ipv4NodesSchema(Schema):
    """
    Ipv4 nodes schema class for common fields in management network and
    data network settings.
    """
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    ip_address = fields.Str(validate=Ipv4(), required=True)
    hostname = fields.Str(required=True)
    gateway = fields.Str(validate=Ipv4(), required=True)
    netmask = fields.Str(validate=Ipv4(), required=True)

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
    hostname = fields.Str(required=True)
    dns_servers = fields.List(fields.Str(required=True))
    search_domain = fields.List(fields.Str(required=True))

class DnsNetworkSettingsSchema(Schema):
    """
    Schema for dns network settings grouped with nested schema classes like
    dns network setting nodes.
    Dns network settings schema class is used to form system config settings schema
    """
    is_external_load_balancer = fields.Boolean(allow_none=True)
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
    smtp_protocol = fields.Str(validate=validate.Length(min=3, max=32),
                               allow_none=True)  # TODO: validate as enum
    smtp_sender_email = fields.Email(allow_none=True)
    smtp_sender_password = fields.Str(validate=validate.Length(min=4, max=64),
                                      allow_none=True)
    email = fields.Str(allow_none=True)

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
    ldap = fields.Nested(LdapConfigSchema, allow_none=True,unknown='EXCLUDE')

@CsmView._app_routes.view("/api/v1/sysconfig")
class SystemConfigListView(CsmView):
    """
    System Configuration related routes
    """

    def __init__(self, request):
        super(SystemConfigListView, self).__init__(request)
        self._service = self.request.app["system_config_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching user config
    """

    async def get(self):
        Log.debug("Handling system config fetch request")

        return await self._service.get_system_config_list()

    """
    POST REST implementation for creating a system config
    """

    async def post(self):
        Log.debug("Handling system config post request")
        try:
            schema = SystemConfigSettingsSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid request body: {}".format(val_err))
        return await self._service.create_system_config(str(uuid.uuid4()),
                                                        **config_data)

@CsmView._app_routes.view("/api/v1/sysconfig/{config_id}")
class SystemConfigView(CsmView):
    def __init__(self, request):
        super(SystemConfigView, self).__init__(request)
        self._service = self.request.app["system_config_service"]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching system config
    """

    async def get(self):
        Log.debug("Handling system config fetch request")

        id = self.request.match_info["config_id"]
        return await self._service.get_system_config_by_id(id)

    """
    PUT REST implementation for creating a system config
    """

    async def put(self):
        Log.debug("Handling system config put request")

        try:
            id = self.request.match_info["config_id"]
            schema = SystemConfigSettingsSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid request body: {}".format(val_err))
        return await self._service.update_system_config(id, config_data)

@CsmView._app_routes.view("/api/v1/sysconfig_helpers/email_test")
class TestEmailView(CsmView):
    def __init__(self, request):
        super().__init__(request)
        self._service = self.request.app["system_config_service"]

    """
    POST REST implementation for sendting test emails
    """

    async def post(self):
        Log.debug("Handling system config email test request")

        try:
            schema = EmailConfigSchema()
            config_data = schema.load(await self.request.json(),
                                      unknown='EXCLUDE')
        except json.decoder.JSONDecodeError:
            raise InvalidRequest(message_args="Request body missing")
        except ValidationError as val_err:
            raise InvalidRequest(
                "Invalid request body: {}".format(val_err))
        return await self._service.test_email_config(config_data)
