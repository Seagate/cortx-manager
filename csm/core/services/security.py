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

import os
import asyncio
import syslog
from datetime import datetime
from string import Template
from typing import Union
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from csm.common.errors import (CsmInternalError, CsmError, CsmTypeError,
                               ResourceExist, CsmNotFoundError, CsmServiceConflict)
from cortx.utils.conf_store.conf_store import Conf
from csm.common.fs_utils import FSUtils
from csm.common.services import ApplicationService
from cortx.utils.log import Log
from cortx.utils.data.db.db_provider import DataBaseProvider
from csm.core.data.models.system_config import (CertificateConfig, SecurityConfig,
                                                CertificateInstallationStatus)
from csm.core.services.file_transfer import FileRef
from csm.plugins.cortx.provisioner import ProvisionerPlugin
from csm.core.data.models.upgrade import ProvisionerCommandStatus
from csm.core.blogic import const
from csm.core.services.iem import IemAppService, IemPayload


CERT_BASE_TMP_DIR = "/tmp/.new"
CERT_CORTX_TMP_DIR = f"{CERT_BASE_TMP_DIR}/cortx/"  # Certificates for both S3 and CSM services

DATE_TEMPLATE = "%m-%d-%Y_%H:%M:%S.%f"


class SecurityService(ApplicationService):
    """
    Service for security management:

    1. Certificates management
    2. Validation responsibilities

    """

    CERT_DIR_BASE_NAME_TEMPLATE = "${USER}_${TIME_STAMP}"
    CONFIG_ID = 1  # for storing actual TLS configuration only one instance is needed
    _MAP = {
        ProvisionerCommandStatus.InProgress: CertificateInstallationStatus.IN_PROGRESS,
        ProvisionerCommandStatus.Success: CertificateInstallationStatus.INSTALLED,
        ProvisionerCommandStatus.Failure: CertificateInstallationStatus.FAILED,
        ProvisionerCommandStatus.NotFound: CertificateInstallationStatus.UNKNOWN,
        ProvisionerCommandStatus.Unknown: CertificateInstallationStatus.UNKNOWN
    }

    def __init__(self, database: DataBaseProvider, provisioner: ProvisionerPlugin):
        super().__init__()
        self._fs_utils = FSUtils()
        self._cert_dir_base_name = Template(self.CERT_DIR_BASE_NAME_TEMPLATE)
        self._certificate_storage = database(CertificateConfig)
        self._security_storage = database(SecurityConfig)
        self._provisioner = provisioner
        self._last_configuration = None
        self._provisioner_id = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._iem_service = IemAppService()

    def _provisioner_to_installation_status(self, prv_status: ProvisionerCommandStatus):
        """ Convert provisioner job status into corresponding certificate installation status
        :param str prv_status: provisioner status enum value
        :return: return one of the `CertificateInstallationStatus` values
        """
        return self._MAP.get(prv_status, CertificateInstallationStatus.UNKNOWN)

    def _load_certificate(self, path: str):
        """
        Helper method for loading certificate from file in X.509 format

        :param path: path to certificate file
        :return: certificate object
        """
        try:
            with open(path, "br") as f:
                # read certificate data as binary
                data = f.read()
            cert = x509.load_pem_x509_certificate(data, default_backend())
            return cert
        except FileNotFoundError as e:
            Log.error(f"Security certificate not available.{e}")
            raise CsmNotFoundError("Security certificate not available.")
        except Exception as e:
            # TODO: Catch proper exceptions instead of generic Exception
            # TODO: Consider to raise another exceptions (SyntaxError?)
            Log.error(f"Cannot load certificate from .pem file: {e}")
            raise CsmInternalError(f"Cannot load certificate from .pem file: {e}")

    async def _store_to_db(self, user: str, pemfile_path: str, save_time: datetime):
        """
        Method to transform information about certificates and private keys to appropriate CSM
        models and store these models into db

        :param user: user who is uploading the certificate and private key
        :param private_key_path: path to the file which stores private key
                                 and corresponding certificate
        :param save_time: python's datetime object which represents certificate and private key
                          uploading time
        :return:
        """
        cert = self._load_certificate(pemfile_path)

        certificate_conf = CertificateConfig()
        certificate_conf.certificate_id = hex(cert.serial_number)[2:]
        certificate_conf.date = save_time
        certificate_conf.user = user
        certificate_conf.pemfile_path = pemfile_path

        try:
            await self._certificate_storage.store(certificate_conf)
        except Exception as e:
            raise CsmInternalError(f"Unable to store certificate information into database: {e}")

        security_conf = SecurityConfig()
        security_conf.config_id = self.CONFIG_ID
        security_conf.s3_config = certificate_conf
        security_conf.csm_config = certificate_conf
        security_conf.provisioner_id = None
        security_conf.update_status(CertificateInstallationStatus.NOT_INSTALLED)

        try:
            await self._security_storage.store(security_conf)
        except Exception as e:
            raise CsmInternalError(f"Unable to store certificate information into database: {e}")

        self._last_configuration = security_conf

    async def store_security_bundle(self, user: str, pemfile_name: str, pemfile_ref: FileRef):
        """
        Method to store uploaded private key and corresponding certificate into the drive

        :param user: user who is uploading the certificate and private key
        :param pemfile_name: archive with security bundle which contains private key and
                             certificate
        :param pemfile_ref: bundle archive reference
        :return:
        """

        saving_time = datetime.now()
        time_stamp = saving_time.strftime(DATE_TEMPLATE)
        cert_dir = self._cert_dir_base_name.substitute(USER=user,
                                                       TIME_STAMP=time_stamp)
        cert_dir = os.path.join(CERT_CORTX_TMP_DIR, cert_dir)
        if not os.path.exists(cert_dir):
            try:
                self._fs_utils.create_dir(cert_dir)
            except CsmTypeError:
                raise  # throw the exception to the controller
            except CsmInternalError:
                raise  # throw the exception to the controller

        try:
            pemfile_ref.save_file(cert_dir, pemfile_name)
        except CsmInternalError as e:
            raise CsmInternalError("An error occurs during saving credentials into "
                                   "the system drive. See logs for more details.") from e

        try:
            await self._store_to_db(user, os.path.join(cert_dir, pemfile_name), saving_time)
        except CsmError as e:
            raise CsmInternalError(f"Error during saving certificates configuration onto database: {e}")

    async def delete_certificate(self, serial_number):
        """
        Delete certificate by serial number

        :return:
        """
        pass

    async def install_certificate(self):
        """
        Install new private key and its corresponding certificate for the CORTX

        :return:
        """
        # await self.verify_security_bundle()  # TODO: add a certificate validation

        if self._last_configuration is None:
            # try to obtain last stored information from db
            self._last_configuration = await self._security_storage.get_by_id(self.CONFIG_ID)

        if self._last_configuration is not None:
            if self._last_configuration.is_not_installed:
                # TODO: in future we can support different pemfiles for each services:
                #  S3, CSM, NodeJS
                source = self._last_configuration.csm_config.pemfile_path
                _provisioner_id = await self._provisioner.set_ssl_certs(source=source)

                self._last_configuration.update_status(CertificateInstallationStatus.IN_PROGRESS)
                self._last_configuration.provisioner_id = _provisioner_id

                await self._update_configuration()
            else:
                if self._last_configuration.is_installed:
                    raise ResourceExist("Last uploaded configuration is already installed")

                # get update certificate installation status to raise correct exception
                await self._update_certificate_installation_status()

                message = "Csm installation conflict"
                if self._last_configuration.is_unknown:
                    message = "Certificate Installation status is unknown"
                elif self._last_configuration.is_pending_status:
                    message = "Certificate Installation in progress"
                elif self._last_configuration.is_failed:
                    message = "Certificate Installation failed"

                raise CsmServiceConflict(message)
        else:
            raise CsmNotFoundError("Don't find last uploaded certificates")

        # TODO: set enable param in Security configuration

    async def _update_configuration(self):
        """Update security configuration in db"""
        if self._last_configuration is not None:
            try:
                await self._security_storage.store(self._last_configuration)
            except Exception as e:
                raise CsmInternalError(f"Can't save into db update security configuration: {e}")

    async def _update_certificate_installation_status(self):
        """
        Update Certificate installation status
        """
        if all(i is not None
               for i in (self._last_configuration, self._last_configuration.provisioner_id)):

            prv_response = await self._provisioner.get_provisioner_job_status(
                                                            self._last_configuration.provisioner_id)

            prv_status = prv_response.status
            self._last_configuration.update_status(
                                            self._provisioner_to_installation_status(prv_status))

            await self._update_configuration()

    async def get_certificate_installation_status(self) -> Union[None, SecurityConfig]:
        """
        Get last certificate installation status
        """
        if self._last_configuration is None:
            # try to obtain last stored information from db
            self._last_configuration = await self._security_storage.get_by_id(self.CONFIG_ID)

        if self._last_configuration is not None:
            if self._last_configuration.is_pending_status:

                if self._last_configuration.provisioner_id is None:
                    Log.debug("Provisioner id of last stored configuration is None")

                    # Update status
                    self._last_configuration.update_status(CertificateInstallationStatus.UNKNOWN)

                    await self._update_configuration()

                else:
                    await self._update_certificate_installation_status()

            return SecurityConfig(self._last_configuration.to_primitive())

        return None  # no uploaded certificates

    async def verify_security_bundle(self):
        """
        Verify newly uploaded security bundle (private key and corresponding certificate):

        Planning:
        1. Verify domain name of certificate
        2. Verify that certificate corresponds to the uploaded private key
        3. Verify that certificate is valid and is not listed

        :return:
        """
        pass

    async def get_certificate_expiry_time(self):
        path = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS>certificate_path")
        def load():
            return self._load_certificate(path)
        cert = await self._loop.run_in_executor(self._executor, load)
        return cert.not_valid_after

    async def _timer_task(self, handler, start: datetime, interval: timedelta):
        current = datetime.now(timezone.utc)
        while True:
            delta = (start - current).total_seconds()
            if delta > 0:
                await asyncio.sleep(delta)

            current = datetime.now(timezone.utc)
            await handler(current)

            current = datetime.now(timezone.utc)
            start = start + interval

    async def _local_timezone(self, from_time):
        """
        Convert utc aware time to local timezone and print in specific format
        """
        converted_time_ltz = from_time.astimezone()
        return converted_time_ltz.strftime(const.CERT_TIME_FORMAT)

    async def _check_certificate_expiry_time(self, current_time):
        warning_days = Conf.get(const.CSM_GLOBAL_INDEX, "SECURITY>ssl_cert_expiry_warning_days")
        try:
            expiry_time = await self.get_certificate_expiry_time()
            expiry_time = expiry_time.replace(tzinfo=timezone.utc)
            expiry_time_ltz = await self._local_timezone(expiry_time)
            days_left = (expiry_time.date() - current_time.date()).days
            if expiry_time < current_time:
                message = f'SSL certificate expired on {expiry_time_ltz}'
            elif days_left in warning_days:
                message = f'SSL certificate will expire on {expiry_time_ltz} - {days_left} day(s) left'
            else:
                message = None

            if message:
                if self._iem_service:
                    Log.warn(f'{message}')
                    self._iem_service.init()
                    severity = self._iem_service.severity_levels['WARN']
                    module = self._iem_service.modules['SSL_EXPIRY']
                    # event_id is not finalized yet. Using a dummy value.
                    payload = IemPayload(severity=severity, module=module, \
                        event_id= 100, message_blob=message)
                    self._iem_service.send(payload)
                else:
                    Log.error("Failed to send SSL expiry IEM. IEM service not initialized.")

        except Exception as e:
            Log.error(f'Failed to obtain certificate expiry time: {e}')


    async def check_certificate_expiry_time_task(self):
        today = datetime.now(timezone.utc).date()
        await self._timer_task(
            handler=self._check_certificate_expiry_time,
            start=datetime(today.year, today.month, today.day,
                           tzinfo=timezone.utc),
            interval=timedelta(days=1)
        )

    async def _get_name_details(self, rdns):
        """
        Get x509 Name object details (i.e Subject and Issuer)
        rdns: Relatively Distinguished Names
        """
        name_details = {}
        for name in rdns:
            if name._attributes:
                name_details[name._attributes[0].oid._name] = name._attributes[0].value
        return name_details

    async def get_certificate_details(self):
        """
        Get current certificate details
        """
        path = Conf.get(const.CSM_GLOBAL_INDEX, "HTTPS>certificate_path")
        Log.debug(f"Getting SSL certificate details from {path}")
        cert = self._load_certificate(path)
        cert_details = {}
        subject_details = await self._get_name_details(cert.subject.rdns)
        issuer_details = await self._get_name_details(cert.issuer.rdns)

        cert_details[const.SUBJECT] = subject_details
        cert_details[const.ISSUER] = issuer_details
        cert_details[const.NOT_VALID_AFTER] = cert.not_valid_after
        cert_details[const.NOT_VALID_BEFORE] = cert.not_valid_before
        cert_details[const.SERIAL_NUMBER] = cert.serial_number
        cert_details[const.VERSION] = cert.version

        Log.debug(f"SSL certificate details: {cert_details}")
        return  { const.CERT_DETAILS: cert_details }
