#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          security.py
 Description:       Services for security management

 Creation Date:     02/19/2020
 Author:            Dimitry Didenko

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
from datetime import datetime
from string import Template
from typing import Union

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from csm.common.errors import (CsmInternalError, CsmError, CsmTypeError,
                               ResourceExist, CsmNotFoundError, CsmServiceConflict)
from csm.common.fs_utils import FSUtils
from csm.common.services import ApplicationService
from eos.utils.log import Log
from eos.utils.data.db.db_provider import DataBaseProvider
from csm.core.data.models.system_config import (CertificateConfig, SecurityConfig,
                                                CertificateInstallationStatus)
from csm.core.services.file_transfer import FileRef
from csm.plugins.eos.provisioner import ProvisionerPlugin
from csm.core.data.models.upgrade import ProvisionerCommandStatus


CERT_BASE_TMP_DIR = "/tmp/.new"
CERT_EOS_TMP_DIR = f"{CERT_BASE_TMP_DIR}/eos/"  # Certificates for both S3 and CSM services

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

    def _provisioner_to_installation_status(self, prv_status: ProvisionerCommandStatus):
        """ Convert provisioner job status into corresponding certificate installation status
        :param str prv_status: provisioner status enum value
        :return: return one of the `CertificateInstallationStatus` values
        """
        return self._MAP.get(prv_status, CertificateInstallationStatus.UNKNOWN)

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
        with open(pemfile_path, "br") as cert_fh:
            # read certificate data as binary
            cert_data = cert_fh.read()
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        except Exception as e:
            raise IndentationError(f"Can't load certificate from .pem file: {e}")
        certificate_conf = CertificateConfig()
        certificate_conf.certificate_id = hex(cert.serial_number)[2:]
        certificate_conf.date = save_time
        certificate_conf.user = user
        certificate_conf.pemfile_path = pemfile_path

        try:
            await self._certificate_storage.store(certificate_conf)
        except Exception as e:
            raise CsmInternalError(f"Unable to store certificate information into db: {e}")

        security_conf = SecurityConfig()
        security_conf.config_id = self.CONFIG_ID
        security_conf.s3_config = certificate_conf
        security_conf.csm_config = certificate_conf
        security_conf.provisioner_id = None
        security_conf.update_status(CertificateInstallationStatus.NOT_INSTALLED)

        try:
            await self._security_storage.store(security_conf)
        except Exception as e:
            raise CsmInternalError(f"Unable to store certificate information into db: {e}")

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
        cert_dir = os.path.join(CERT_EOS_TMP_DIR, cert_dir)
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
            raise CsmInternalError(f"Error during saving certificates configuration onto db: {e}")

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
