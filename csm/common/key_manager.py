"""
 ****************************************************************************
 Filename:          key_manager.py
 Description:       Manager for security material.

 Creation Date:     12/20/2019
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from os import stat, umask
from pathlib import Path, PosixPath

class KeyManager:
    """
    Encapsulates key/certificate creation and access operations.
    """

    class KeyMaterialStore:
        """
        Context manager for safe access to key material store.
        """
        _old_umask: int
        _store_path: Path

        def __init__(self, store_path: str) -> None:
            self._store_path = PosixPath(store_path)

        def __enter__(self) -> Path:
            self._old_umask = umask(0o077)
            self._store_path.mkdir(parents=True, exist_ok=True)
            if stat(self._store_path).st_mode & 0o077:
                raise Exception(f'Key store "{self._store_path}" has compromising permissions')
            return self._store_path

        def __exit__(self, type, value, traceback) -> None:
            umask(self._old_umask)

    @staticmethod
    def create_security_material(store_path: str, name: str):
        with KeyManager.KeyMaterialStore(store_path) as kms:
            file = kms / name
            with file.open('w+'):
                pass

    @staticmethod
    def get_security_material(store_path: str, name: str):
        path = PosixPath(store_path) / name
        path.resolve(strict=True)
        if stat(path).st_mode & 0o077:
            raise Exception(f'Security material "{path}" has compromising permissions.')
        return path
