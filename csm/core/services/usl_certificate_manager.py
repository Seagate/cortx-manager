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

from asyncio import Lock
from csm.core.blogic import const
from cortx.utils.log import Log
from cortx.utils.conf_store import Conf
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import load_pem_x509_certificate
from cortx.utils.security.key_manager import KeyMaterialStore
from cortx.utils.security.secure_storage import SecureStorage
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
    _secure_storage: Optional[SecureStorage]

    def __init__(self, key_material_store: str, private_key: str, certificate: str,
                 secure_storage: Optional[SecureStorage] = None) -> None:
        self._key_material_store_path = str(key_material_store)
        self._private_key_filename = str(private_key)
        self._certificate_filename = str(certificate)
        self._secure_storage = secure_storage

    async def _restore_to_disk(self, filename) -> bool:
        if self._secure_storage is None:
            return False
        data = await self._secure_storage.get(filename)
        if data is None:
            return False
        with KeyMaterialStore(self._key_material_store_path) as kms:
            path = kms.path() / filename
            with open(path, 'wb') as f:
                f.write(data)
        return True

    async def _has_file(self, filename: str) -> bool:
        path = PosixPath(self._key_material_store_path) / filename
        res = path.exists() and path.is_file()
        # If file is not on the disk try to restore from the secure storage
        if not res:
            Log.debug(f'File {filename} is not found on the disk')
            res = await self._restore_to_disk(filename)
            Log.debug(f"File {filename} is{'' if res else 'not'} restored to the disk "
                      f"from the secure storage")
        return res

    async def _has_private_key_file(self) -> bool:
        return await self._has_file(self._private_key_filename)

    async def _has_certificate_file(self) -> bool:
        return await self._has_file(self._certificate_filename)

    async def _get_bytes(self, filename: str, lax: bool = False) -> Optional[bytes]:
        file_exists = await self._has_file(filename)

        if not file_exists:
            return None
        with KeyMaterialStore(self._key_material_store_path) as kms:
            path = kms.resolve_path(filename, lax=lax)
            with open(path, 'r') as f:
                return f.read().encode()

    # FIXME private key should not be exposed
    async def _get_private_key_bytes(self) -> Optional[bytes]:
        return await self._get_bytes(self._private_key_filename)

    async def _get_certificate_bytes(self) -> Optional[bytes]:
        return await self._get_bytes(self._certificate_filename, lax=True)

    # FIXME implement this function so that it does not need access to the private key
    async def _get_public_key_bytes(self) -> Optional[bytes]:
        private_key_bytes = await self._get_private_key_bytes()
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
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        except (TypeError, ValueError, UnsupportedAlgorithm):
            return None
        return public_key_bytes

    async def _store_bytes(self, filename: str, data: bytes, force: bool = False) -> None:
        if self._secure_storage is not None:
            await self._secure_storage.store(filename, data, force=force)
        with KeyMaterialStore(self._key_material_store_path) as kms:
            path = kms.path() / filename
            with open(path, 'wb') as f:
                f.write(data)

    async def _delete_bytes(self, filename: str) -> bool:
        deleted = None
        # Delete the file from the secure storage
        if self._secure_storage is not None:
            try:
                await self._secure_storage.delete(filename)
                deleted = True
            except KeyError:
                # Don't fail if the file is not in the secure storage
                deleted = False
        # Delete the file from the disk
        with KeyMaterialStore(self._key_material_store_path) as kms:
            try:
                f = kms.resolve_path(filename, lax=True)
                f.unlink()
                # Here and below: don't override the secure storage status if exists
                deleted = True if deleted is None else deleted
            except FileNotFoundError:
                # Don't fail if the file is not on the disk
                deleted = False if deleted is None else deleted
        return deleted


class USLNativeCertificateManager(CertificateManager):
    """
    Implements additional logic to manipulate USL native key material.
    """

    __lock = Lock()

    def __init__(self) -> None:
        super().__init__(
            Conf.get(const.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>cert_path_key'),
            Conf.get(const.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>native_key'),
            Conf.get(const.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>native_crt'),
        )

    # FIXME private key should not be exposed
    async def get_private_key_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return await self._get_private_key_bytes()

    async def get_certificate_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return await self._get_certificate_bytes()


class USLDomainCertificateManager(CertificateManager):
    """
    Implements additional logic to manipulate USL domain key material.
    """

    __lock = Lock()

    def __init__(self, secure_storage: SecureStorage) -> None:
        super().__init__(
            Conf.get(const.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>cert_path_key'),
            Conf.get(const.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>domain_key'),
            Conf.get(const.USL_GLOBAL_INDEX, 'UDS_CERTIFICATES>domain_crt'),
            secure_storage
        )

    # FIXME private key should not be exposed
    async def get_private_key_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return await self._get_private_key_bytes()

    async def get_public_key_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return await self._get_public_key_bytes()

    async def get_certificate_bytes(self) -> Optional[bytes]:
        async with type(self).__lock:
            return await self._get_certificate_bytes()

    async def create_private_key_file(self, overwrite: bool = True) -> None:
        async with type(self).__lock:
            file_exists = await self._has_private_key_file()
            if not overwrite and file_exists:
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
            await self._store_bytes(self._private_key_filename, encoded_key, force=overwrite)

    async def create_certificate_file(self, data: bytes) -> None:
        try:
            certificate = load_pem_x509_certificate(data, default_backend())
            public_key_from_certificate = certificate.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        except ValueError:
            raise CertificateError('Invalid certificate data')
        async with type(self).__lock:
            public_key_from_private_key = await self._get_public_key_bytes()
            if public_key_from_private_key is None:
                raise CertificateError('Could not obtain public key bytes')
            if public_key_from_private_key != public_key_from_certificate:
                raise CertificateError('Certificate does not match private key')
            await self._store_bytes(self._certificate_filename, data)

    async def delete_key_material(self) -> bool:
        async with type(self).__lock:
            await self._delete_bytes(self._certificate_filename)
            deleted = await self._delete_bytes(self._private_key_filename)
        return deleted
