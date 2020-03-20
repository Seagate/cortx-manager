"""
 ****************************************************************************
 Filename:          usl_certificate_manager.py
 Description:       Services for USL calls

 Creation Date:     01/30/2020
 Author:            Tadeu Bastos

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from asyncio import Lock
from csm.core.blogic import const
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import load_pem_x509_certificate
from eos.utils.security.key_manager import KeyMaterialStore
from pathlib import PosixPath
from typing import Optional


class CertificateError(Exception):
    """
    Represents errors on certificate handling operations.
    """
    pass


class CertificateManager:
    """
    Encapsulates USL key material management features.
    """

    _key_material_store_path: str
    _private_key_filename: str
    _certificate_filename: str

    def __init__(self, key_material_store: str, private_key: str, certificate: str) -> None:
        self._key_material_store_path = str(key_material_store)
        self._private_key_filename = str(private_key)
        self._certificate_filename = str(certificate)

    def _has_private_key_file(self) -> bool:
        path = PosixPath(self._key_material_store_path) / self._private_key_filename
        return path.exists() and path.is_file()

    def _has_certificate_file(self) -> bool:
        path = PosixPath(self._key_material_store_path) / self._certificate_filename
        return path.exists() and path.is_file()

    def _get_bytes(self, filename: str, lax: bool = False) -> Optional[bytes]:
        with KeyMaterialStore(self._key_material_store_path) as kms:
            try:
                path = kms.resolve_path(filename, lax=lax)
            except FileNotFoundError:
                return None
            with open(path, 'r') as f:
                return f.read().encode()

    # FIXME private key should not be exposed
    def _get_private_key_bytes(self) -> Optional[bytes]:
        return self._get_bytes(self._private_key_filename)

    def _get_certificate_bytes(self) -> Optional[bytes]:
        return self._get_bytes(self._certificate_filename, lax=True)

    # FIXME implement this function so that it does not need access to the private key
    def _get_public_key_bytes(self) -> Optional[bytes]:
        private_key_bytes = self._get_private_key_bytes()
        if private_key_bytes is None:
            return None
        try:
            private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None,
                backend=default_backend(),
            )
            public_key = private_key.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.PKCS1
            )
        except (TypeError, ValueError, UnsupportedAlgorithm):
            return None
        return public_key_bytes


class USLNativeCertificateManager(CertificateManager):
    """
    Implements additional logic to manipulate USL native key material.
    """

    __lock = Lock()

    def __init__(self) -> None:
        super().__init__(
            const.UDS_CERTIFICATES_PATH,
            const.UDS_NATIVE_PRIVATE_KEY_FILENAME,
            const.UDS_NATIVE_CERTIFICATE_FILENAME,
        )

    # FIXME private key should not be exposed
    async def get_private_key_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return self._get_private_key_bytes()

    async def get_certificate_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return self._get_certificate_bytes()


class USLDomainCertificateManager(CertificateManager):
    """
    Implements additional logic to manipulate USL domain key material.
    """

    __lock = Lock()

    def __init__(self) -> None:
        super().__init__(
            const.UDS_CERTIFICATES_PATH,
            const.UDS_DOMAIN_PRIVATE_KEY_FILENAME,
            const.UDS_DOMAIN_CERTIFICATE_FILENAME,
        )

    # FIXME private key should not be exposed
    async def get_private_key_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return self._get_private_key_bytes()

    async def get_public_key_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return self._get_public_key_bytes()

    async def get_certificate_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return self._get_certificate_bytes()

    async def create_private_key_file(self, overwrite: bool = True) -> None:
        async with type(self).__lock:
            with KeyMaterialStore(self._key_material_store_path) as kms:
                if not overwrite and self._has_private_key_file():
                    return
                key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=4096,
                    backend=default_backend(),
                )
                encoded_key = key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                path = kms.path() / self._private_key_filename
                with open(path, 'wb') as f:
                    f.write(encoded_key)

    async def create_certificate_file(self, data: bytes) -> None:
        try:
            certificate = load_pem_x509_certificate(data, default_backend())
            public_key_from_certificate = certificate.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.PKCS1,
            )
        except ValueError:
            raise CertificateError('Invalid certificate data')
        async with type(self).__lock:
            public_key_from_private_key = self._get_public_key_bytes()
            if public_key_from_private_key is None:
                raise CertificateError('Could not obtain public key bytes')
            if public_key_from_private_key != public_key_from_certificate:
                raise CertificateError('Certificate does not match private key')
            with KeyMaterialStore(self._key_material_store_path) as kms:
                path = kms.path() / self._certificate_filename
                with open(path, 'wb') as f:
                    f.write(data)

    async def delete_key_material(self) -> None:
        async with type(self).__lock:
            with KeyMaterialStore(self._key_material_store_path) as kms:
                private_key = kms.resolve_path(self._private_key_filename, lax=True)
                private_key.unlink()
                try:
                    certificate = kms.resolve_path(self._certificate_filename, lax=True)
                    certificate.unlink()
                except FileNotFoundError:
                    # This command should not fail if certificate is not present
                    pass
