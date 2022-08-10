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


from cryptography import x509
from cryptography.hazmat.backends import default_backend
from abc import ABCMeta, abstractmethod
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.common.errors import (CsmInternalError,CsmNotFoundError)

class Certificate(metaclass=ABCMeta):

    @abstractmethod
    def get_certificate_details(self):
        raise Exception('get_certificate_details not implemented in Ceritifcate class')

class SSLCertificate(Certificate):

    def __init__(self, path):
        self.path = path

    def get_certificate_details(self):
        """
        Get certificate details
        """
        Log.info(f"Getting SSL certificate details from {self.path}")
        cert = self._load_certificate(self.path)
        cert_details = {}
        subject_details = self._get_name_details(cert.subject.rdns)
        issuer_details = self._get_name_details(cert.issuer.rdns)

        cert_details[const.SUBJECT] = subject_details
        cert_details[const.ISSUER] = issuer_details
        cert_details[const.NOT_VALID_AFTER] = str(cert.not_valid_after)
        cert_details[const.NOT_VALID_BEFORE] = str(cert.not_valid_before)
        cert_details[const.SERIAL_NUMBER] = cert.serial_number
        cert_details[const.VERSION] = str(cert.version)

        Log.debug(f"SSL certificate details: {cert_details}")
        return  { const.CERT_DETAILS: cert_details }

    def _load_certificate(self, path: str):
        """
        Helper method for loading certificate from file in X.509 format

        :param path: path to certificate file
        :return: certificate object
        """
        try:
            with open(path, "br") as f:
                data = f.read()
            cert = x509.load_pem_x509_certificate(data, default_backend())
            return cert
        except FileNotFoundError as e:
            Log.error(f"Security certificate not available.{e}")
            raise CsmNotFoundError("Security certificate not available.")
        except Exception as e:
            # TODO: Catch proper exceptions instead of generic Exception
            # TODO: Consider to raise another exceptions (SyntaxError?)
            Log.error(f"Unable to load certificate information: {e}")
            raise CsmInternalError("Unable to load certificate information.")

    def _get_name_details(self, rdns):
        """
        Get x509 Name object details (i.e Subject and Issuer)
        rdns: Relatively Distinguished Names
        """
        name_details = {}
        for name in rdns:
            if name._attributes:
                name_details[name._attributes[0].oid._name] = name._attributes[0].value
        return name_details
