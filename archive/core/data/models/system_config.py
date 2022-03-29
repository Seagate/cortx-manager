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

from datetime import datetime, timezone
from enum import Enum

from schematics.models import Model
from schematics.types import (StringType, ModelType, ListType,
                              BooleanType, DateTimeType, IntType)

from cortx.utils.log import Log
from csm.common.email import SmtpServerConfiguration
from csm.core.blogic import const
from csm.core.blogic.models import CsmModel

# Schematics models to form schema structure for system configuration settings
class Ipv4Nodes(Model):
    """
    Ipv4 nodes common fields in management network and data network settings.
    """
    id = IntType()
    name = StringType()
    ip_address = StringType()
    hostname = StringType()
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

class Ipv4Base(Model):
    """
    Class hold common fields in ipv4 for management network and data network settings.
    """
    is_dhcp = BooleanType()
    nodes = ListType(ModelType(Ipv4Nodes))

class ManagementNetworkIpv6(Model):
    """
    Ipv6 nested model used to form management network settings schema.
    """
    is_dhcp = BooleanType()
    ip_address = ListType(StringType)
    gateway = StringType()
    address_label = StringType()
    type = StringType()

class ManagementNetworkSettings(Model):
    """
    Model for management network settings grouped with ipv4 and ipv6.
    Model is used to form system config settings schema
    """
    ipv4 = ModelType(Ipv4Base)
    ipv6 = ModelType(ManagementNetworkIpv6)

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
    ipv4 = ModelType(Ipv4Base)
    ipv6 = ModelType(DataNetworkSettingsIpv6)

class DnsNetworkSettingsNodes(Model):
    """
    Dns nodes nested model used to form dns network settings schema.
    """
    id = IntType()
    name = StringType()
    dns_servers = ListType(StringType)
    search_domain = ListType(StringType)

class DnsNetworkSettings(Model):
    """
    Model for dns network settings grouped with dns nodes.
    Model is used to form system config settings schema
    """
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

# TODO: figure out exact constants
EMAIL_CONFIG_SMTP_TLS_PROTOCOL = 'tls'
EMAIL_CONFIG_SMTP_SSL_PROTOCOL = 'ssl'
EMAIL_CONFIG_SMTP_STARTTLS_PROTOCOL = 'starttls'

class EmailConfig(Model):
    """
    Email config nested model used to form Notification schema.
    """
    smtp_server = StringType()
    smtp_port = IntType()
    smtp_protocol = StringType()  # TODO: what values can it take?
    smtp_sender_email = StringType()
    smtp_sender_password = StringType()
    email = StringType()

    def update(self, new_values: dict):
        """
        A method to update the email config model.
        param: new_values : Dictionary containg email config payload
        """
        for key in new_values:
            setattr(self, key, new_values[key])

    def get_target_emails(self):
        """
        Returns a list of emails to send notifications to
        :returns: list of strings
        """
        stripped = (x.strip() for x in self.email.split(','))
        return [x for x in stripped if x]

    def to_smtp_config(self) -> SmtpServerConfiguration:
        config = SmtpServerConfiguration()
        config.smtp_host = self.smtp_server
        config.smtp_port = self.smtp_port
        config.smtp_login = self.smtp_sender_email
        config.smtp_password = self.smtp_sender_password
        config.smtp_use_ssl = self.smtp_protocol.lower() in \
            [EMAIL_CONFIG_SMTP_SSL_PROTOCOL, EMAIL_CONFIG_SMTP_TLS_PROTOCOL]
        config.smtp_use_starttls = self.smtp_protocol.lower() == EMAIL_CONFIG_SMTP_STARTTLS_PROTOCOL
        config.ssl_context = None
        config.timeout = const.CSM_SMTP_SEND_TIMEOUT_SEC
        config.reconnect_attempts = const.CSM_SMTP_RECONNECT_ATTEMPTS
        return config

class SyslogConfig(Model):
    """
    Syslog config nested model used to form Notification schema.
    """
    syslog_server = StringType()
    syslog_port = IntType()

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


class CertificateConfig(CsmModel):
    """
    Certificate and private key configuration for the system servers
    """

    _id = "certificate_id"
    certificate_id = StringType()  # id of certificate configuration: certificate serial number
    date = DateTimeType()  # certificate uploading time
    user = StringType()  # User who uploaded certificate
    pemfile_path = StringType()


class CertificateInstallationStatus(Enum):
    """Enum represents current intallation status for certificate installation
    """

    NOT_INSTALLED = "not_installed"
    INSTALLED = "installation_successful"
    FAILED = "installation_failed"
    IN_PROGRESS = "in_progress"
    UNKNOWN = "unknown"


class SecurityConfig(CsmModel):
    """
    System Security configuration: certificates settings and so on
    """

    _id = "config_id"
    config_id = IntType()
    s3_config = ModelType(CertificateConfig)
    csm_config = ModelType(CertificateConfig)
    provisioner_id = IntType()
    installation_status = StringType()

    @property
    def is_pending_status(self) -> bool:
        """Check installation status and return True if need to refresh installation
        status and False otherwise
        """
        if (self.installation_status == CertificateInstallationStatus.IN_PROGRESS.value or
                self.installation_status == CertificateInstallationStatus.UNKNOWN.value):
            return True

        return False

    @property
    def is_installed(self) -> bool:
        """Check if certificate is already installed or not

        :return: True if certificate installed and False otherwise
        """
        return (True if self.installation_status == CertificateInstallationStatus.INSTALLED.value
                else False)

    @property
    def is_failed(self) -> bool:
        """Check if certificate installation failed or not

        :return: True if certificate installation was failed and false otherwise
        """
        return (True if self.installation_status == CertificateInstallationStatus.FAILED.value
                else False)

    @property
    def is_unknown(self) -> bool:
        """Check if certificate installation status is unkown

        :return: True if certificate installation status is unkown and False otherwise
        """
        return (True if self.installation_status == CertificateInstallationStatus.UNKNOWN.value
                else False)

    @property
    def is_not_installed(self) -> bool:
        """Check if certificate not installed

        :return: True if certificate is not installed and False otherwise
        """
        return (True
                if self.installation_status == CertificateInstallationStatus.NOT_INSTALLED.value
                else False)

    def update_status(self, status: CertificateInstallationStatus):
        self.installation_status = status.value


class ApplianceName(CsmModel):
    _id = 'value'

    value = 'value' # FIXME workaround to ensure there is only one database entry
    appliance_name = StringType(regex='^[A-Za-z0-9_-]{2,255}$')

    @staticmethod
    def instantiate(appliance_name: str) -> 'ApplianceName':
        instance = ApplianceName()
        instance.appliance_name = appliance_name
        return instance

    def __str__(self) -> str:
        return self.appliance_name


class SystemConfigSettings(CsmModel):
    """
    Model for complete system config settings grouped with nested models like management network,
    data network, dns network, date time, notification and ldap settings.
    """
    _id = "config_id"
    config_id = StringType()
    appliance_name = ModelType(ApplianceName)
    management_network_settings = ModelType(ManagementNetworkSettings)
    data_network_settings = ModelType(DataNetworkSettings)
    dns_network_settings = ModelType(DnsNetworkSettings)
    date_time_settings = ModelType(DateTimeSettings)
    notifications = ModelType(Notification)
    is_summary = BooleanType()
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
        system_config.appliance_name = None
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

class License(CsmModel):
    """
    Base model for license key
    """
    async def update(self, new_values: dict):
        """
        Method to update the license model.
        param: new_values : Dictionary containg license key payload
        return:
        """
        for key in new_values:
            setattr(self, key, new_values[key])

class OnboardingLicense(License):
    """
    Data model to store on boarding license key
    """
    _id = 'csm_onboarding_license_key'

    csm_onboarding_license_key = StringType()

    def __init__(self, license_key: str, *args, **kwargs):
        super(OnboardingLicense, self).__init__(*args, **kwargs)
        self.csm_onboarding_license_key = license_key
