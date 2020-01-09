"""
 ****************************************************************************
 Filename:          system_config.py
 Description:       Contains System Config models and definitions

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

import base64
from datetime import datetime, timezone

from schematics.models import Model
from schematics.types import (StringType, ModelType, ListType,
                              BooleanType, DateTimeType, IntType)

from csm.common.log import Log
from csm.core.blogic.models.base import CsmModel

# Schematics models to form schema structure for system configuration settings
class Ipv4Nodes(Model):
    """
    Ipv4 nodes common fields in management network and data network settings.
    """
    id = IntType()
    vip_address = StringType()
    ip_address = StringType()
    gateway = StringType()
    netmask = StringType()

class Ipv6Nodes(Model):
    """
    Ipv6 nodes common fields in management network and data network settings.
    """
    id = IntType()
    ip_address = ListType(StringType)
    gateway = StringType()
    address_label = StringType()
    type = StringType()

class ManagementNetworkBase(Model):
    """
    Class hold common fields for management network settings.
    """
    is_dhcp = BooleanType()

class ManagementNetworkIpv4(ManagementNetworkBase):
    """
    Ipv4 nested model used to form management network settings schema.
    """
    nodes = ListType(ModelType(Ipv4Nodes))

class ManagementNetworkIpv6(ManagementNetworkBase):
    """
    Ipv6 nested model used to form management network settings schema.
    """
    ip_address = ListType(StringType)
    gateway = StringType()
    address_label = StringType()
    type = StringType()

class ManagementNetworkSettings(Model):
    """
    Model for management network settings grouped with ipv4 and ipv6.
    Model is used to form system config settings schema
    """
    ipv4 = ModelType(ManagementNetworkIpv4)
    ipv6 = ModelType(ManagementNetworkIpv6)

class DataNetworkSettingsIpv4(Model):
    """
    Ipv4 nested model used to form data network settings schema.
    """
    is_dhcp = BooleanType()
    nodes = ListType(ModelType(Ipv4Nodes))

class DataNetworkSettingsIpv6(Model):
    """
    Ipv6 nested model used to form data network settings schema.
    """
    is_auto = BooleanType()
    nodes = ListType(ModelType(Ipv6Nodes))

class DataNetworkSettings(Model):
    """
    Model for data network settings grouped with ipv4 and ipv6 setting.
    Model is used to form system config settings schema
    """
    is_external_load_balancer = BooleanType()
    ipv4 = ModelType(DataNetworkSettingsIpv4)
    ipv6 = ModelType(DataNetworkSettingsIpv6)

class DnsNetworkSettingsNodes(Model):
    """
    Dns nodes nested model used to form dns network settings schema.
    """
    id = IntType()
    dns_servers = ListType(StringType)
    search_domain = ListType(StringType)
    hostname = StringType()

class DnsNetworkSettings(Model):
    """
    Model for dns network settings grouped with dns nodes.
    Model is used to form system config settings schema
    """
    is_external_load_balancer = BooleanType()
    fqdn_name = StringType()
    hostname = StringType()
    nodes = ListType(ModelType(DnsNetworkSettingsNodes))

class Ntp(Model):
    """
    Ntp nested model used to form date time settings schema.
    """
    ntp_server_address = StringType()
    ntp_timezone_offset = StringType()

class ManualDateTime(Model):
    """
    Manual date time nested model used to form date time settings schema.
    """
    date = StringType()
    hour = StringType()
    minute = StringType()
    clock = StringType()

class DateTimeSettings(Model):
    """
    Model for date time settings grouped with ntp and manual date time.
    Model is used to form system config settings schema
    """
    is_ntp = BooleanType()
    ntp = ModelType(Ntp)
    date_time = ModelType(ManualDateTime)

class EmailConfig(Model):
    """
    Email config nested model used to form Notification schema.
    """
    stmp_server = StringType()
    smtp_port = IntType()
    smtp_protocol = StringType()
    smtp_sender_email = StringType()
    smtp_sender_password = StringType()
    email = StringType()
    weekly_email = BooleanType()
    send_test_mail = BooleanType()

class SyslogConfig(Model):
    """
    Syslog config nested model used to form Notification schema.
    """
    syslog_server = StringType()
    syslog_port = IntType()
    send_test_syslog = BooleanType()

class Notification(CsmModel):
    """
    Model for Notification grouped with email config and syslog config.
    Model is used to form system config settings schema
    """
    email = ModelType(EmailConfig)
    syslog = ModelType(SyslogConfig)

class LdapConfig(Model):
    """
    Model for ldap config.
    Model is used to form system config settings schema
    """
    user_search_base = StringType()
    server = StringType()
    port = IntType()
    alt_server = StringType()
    alt_port = IntType()

class SystemConfigSettings(CsmModel):
    """
    Model for complete system config settings grouped with nested models like management network,
    data network, dns network, date time, notification and ldap settings.
    """
    _id = "config_id"
    config_id = StringType()
    management_network_settings = ModelType(ManagementNetworkSettings)
    data_network_settings = ModelType(DataNetworkSettings)
    dns_network_settings = ModelType(DnsNetworkSettings)
    date_time_settings = ModelType(DateTimeSettings)
    notifications = ModelType(Notification)
    ldap = ModelType(LdapConfig)
    updated_time = DateTimeType()
    created_time = DateTimeType()

    # TODO: Implement password encryption/decryption with finalized design in future.
    async def update(self, new_values: dict):
        """
        Method to update the system config settings model.
        param: new_values : Dictionary containg system config payload
        return: 
        """
        sender_password = ""
        password = ""
        if self.notifications and self.notifications.email:
            password = self.notifications.email.smtp_sender_password
        for key in new_values:
            setattr(self, key, new_values[key])
        self.updated_time = datetime.now(timezone.utc)
        if "notifications" in new_values and new_values["notifications"]:
            if "email" in new_values.get("notifications") and \
                    new_values["notifications"]["email"]:
                sender_password = new_values.get('notifications', {}). \
                    get('email', {}).get('smtp_sender_password', {})
        if sender_password and password != sender_password:
            """
            Converting the string type password to bytes as required by
            urlsafe_b64encode
            """
            sender_password_bytes = base64.urlsafe_b64encode(
                sender_password.encode())
            """
            Converting to string for saving in KVS. The decode() method converts
            the encrypted field from binary to string.
            """
            self.notifications.email.smtp_sender_password = sender_password_bytes.decode()

    @staticmethod
    def instantiate_system_config(config_id):
        """
        Instantiate system config settings class.
        param config_id: ID of the system config.
        return: SystemConfigSettings model object.
        """
        system_config = SystemConfigSettings()
        system_config.config_id = config_id
        system_config.notifications = Notification()
        system_config.notifications.email = EmailConfig()
        system_config.ldap = LdapConfig()
        system_config.notifications.syslog = SyslogConfig()
        system_config.created_time = datetime.now(timezone.utc)
        system_config.updated_time = datetime.now(timezone.utc)
        return system_config

    def to_primitive(self) -> dict:
        """
        Converts the system config settings object to dict.
        params: None
        return: system config settings model as a dict .
        """
        obj = super().to_primitive()
        try:
            if 'created_time' in obj:
                obj.pop('created_time', None)
            if 'updated_time' in obj:
                obj.pop('updated_time', None)
        except Exception as ex:
            Log.exception(ex)
        return obj
