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

from datetime import datetime, timezone

from schematics.models import Model
from schematics.types import (StringType, ModelType, ListType,
                              BooleanType, DateTimeType, IntType)

from csm.common.log import Log
from csm.core.blogic.models.base import CsmModel

# Schematics models to store system configuration settings
class ManagementNetworkSettingsIpv4(Model):
    """ Model for management network settings ipv4 """
    is_dhcp = BooleanType()
    ip_address = StringType()
    netmask = StringType()
    gateway = StringType()

class ManagementNetworkSettingsIpv6(Model):
    """ Model for management network settings ipv6 """
    is_dhcp = BooleanType()
    ip_address = ListType(StringType)
    gateway = StringType()
    address_label = StringType()
    type = StringType()

class ManagementNetworkSettings(Model):
    """ Model for management network settings """
    ipv4 = ModelType(ManagementNetworkSettingsIpv4)
    ipv6 = ModelType(ManagementNetworkSettingsIpv6)

class DataNetworkSettingsIpv4Nodes(Model):
    """ Model for data network settings ipv4 nodes """
    id = IntType()
    ip_address = StringType()
    netmask = StringType()
    gateway = StringType()

class DataNetworkSettingsIpv6Nodes(Model):
    """ Model for data network settings ipv6 nodes """
    id = IntType()
    ip_address = ListType(StringType)
    gateway = StringType()
    address_label = StringType()
    type = StringType()

class DataNetworkSettingsIpv4(Model):
    """ Model for data network settings ipv4 """
    is_dhcp = BooleanType()
    nodes = ListType(ModelType(DataNetworkSettingsIpv4Nodes))

class DataNetworkSettingsIpv6(Model):
    """ Model for data network settings ipv6 """
    is_auto = BooleanType()
    nodes = ListType(ModelType(DataNetworkSettingsIpv6Nodes))

class DataNetworkSettings(Model):
    """ Model for data network settings """
    is_external_load_balancer = BooleanType()
    ipv4 = ModelType(DataNetworkSettingsIpv4)
    ipv6 = ModelType(DataNetworkSettingsIpv6)

class DnsNetworkSettingsNodes(Model):
    """ Model for dns network setting nodes """
    id = IntType()
    dns_servers = ListType(StringType)
    search_domain = ListType(StringType)

class DnsNetworkSettings(Model):
    """ Model for dns network settings """
    is_external_load_balancer = BooleanType()
    fqdn_name = StringType()
    hostname = StringType()
    nodes = ListType(ModelType(DnsNetworkSettingsNodes))

class Ntp(Model):
    """ Model for ntp date time settings """
    ntp_server_address = StringType()
    ntp_timezone_offset = StringType()

class ManualDateTime(Model):
    """ Model for manual date time settings """
    date = StringType()
    hour = StringType()
    minute = StringType()
    clock = StringType()

class DateTimeSettings(Model):
    """ Model for date time settings """
    is_ntp = BooleanType()
    ntp = ModelType(Ntp)
    date_time = ModelType(ManualDateTime)

class SystemConfigSettings(CsmModel):
    """ Model for all system configuration settings """
    _id = "config_id"
    config_id = StringType()
    management_network_settings = ModelType(ManagementNetworkSettings)
    data_network_settings = ModelType(DataNetworkSettings)
    dns_network_settings = ModelType(DnsNetworkSettings)
    date_time_settings = ModelType(DateTimeSettings)
    updated_time = DateTimeType()
    created_time = DateTimeType()

    async def update(self, new_values: dict):
        """
        Method to update the system config settings model.
        param: new_values : Dictionary containg system config payload
        return: 
        """
        for key in new_values:
            setattr(self, key, new_values[key])
        self.updated_time = datetime.now(timezone.utc)

    @staticmethod
    def instantiate_system_config(config_id):
        """
        Instantiate system config settings class.
        param config_id: ID of the system config.
        return: SystemConfigSettings model object.
        """
        system_config = SystemConfigSettings()
        system_config.config_id = config_id
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
