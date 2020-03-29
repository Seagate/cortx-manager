#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          fs_utils.py
 Description:       Utils for system management: create, delete, rename files. Correctly
                    handle system exception, access rights, etc.

 Creation Date:     02/26/2020
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
from shutil import make_archive, unpack_archive
import asyncio
import multiprocessing
from enum import Enum
from concurrent.futures import ThreadPoolExecutor


from csm.common.errors import (CsmResourceNotAvailable, CsmTypeError,
                               CsmInternalError, ResourceExist)


class FSUtils:
    """
    Utils for file system management:

    1. Create/Delete/Move directories and files
    2. Handle exceptions due to lack of correct permissions for system operations

    """

    def __init__(self):
        pass

    @staticmethod
    def create_dir(path: str):
        """
        Create directory by a given path. All sub-directories are created recursively

        :param path: path to directory which need to create
        :return:
        """
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as e:
                raise CsmInternalError(f"System error during directory creation for "
                                       f"path='{path}': {e}")
        else:
            raise ResourceExist(f"Can not create directory {path}: it already exists ")

    @staticmethod
    def delete(path):
        """
        Delete file or directory by a given path

        :param path:
        :return:
        """
        if os.path.exists(path):
            if os.path.isdir(path):
                try:
                    os.rmdir(path)
                except OSError as e:
                    raise CsmInternalError(f"System error during directory deletion '{path}': {e}")
            elif os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError as e:
                    raise CsmInternalError(f"System error during file deletion '{path}': {e}")
            elif os.path.islink(path):
                try:
                    os.unlink(path)
                except OSError as e:
                    raise CsmInternalError(f"System error during file unlinking '{path}': {e}")
            else:
                raise CsmTypeError(f"{path} is neither directory nor file/link")

    @staticmethod
    def move(src_path, dst_path):
        """
        Move file or directory from src_path to dst_path

        :param src_path: source path
        :param dst_path: destination path
        :return:
        """
        if os.path.exists(src_path):
            try:
                os.rename(src_path, dst_path)
            except OSError as e:
                raise CsmInternalError(f"System error during directory moving from '{src_path}' to "
                                       f"'{dst_path}': {e}")
        else:
            raise CsmResourceNotAvailable(f"Source path '{src_path}' is not exists")


class ArchiveFormats(Enum):
    """Archive formats to perform extracting and packing operations"""

    ZIP = "zip"  # based on zlib module
    TAR = "tar"  # based on zlib module
    GZTAR = "gztar"  # based on zlib module
    BZTAR = "bztar"  # based on bz2 module
    XZTAR = "xztar"  # bazed on lzma module


class Archivator:
    """Base class to perform packing/unpacking operations"""

    def __init__(self, thread_pool_exec: ThreadPoolExecutor=None,
                 loop: asyncio.AbstractEventLoop=None):
        self._pool = (ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
                      if thread_pool_exec is None else thread_pool_exec)
        self._loop = asyncio.get_event_loop() if loop is None else loop

    async def make_archive(self, base_name, format=ArchiveFormats.GZTAR.value,
                           root_dir=None, base_dir=None):

        def _make_archive(_base_name, _format, _root_dir, _base_dir):
            # imported function validates correctness/existence of archive and directories itself
            make_archive(base_name=_base_name, format=_format,
                         root_dir=_root_dir, base_dir=_base_dir)
        result = await self._loop.run_in_executor(self._pool, _make_archive,
                                                  base_name, format, root_dir, base_dir)

    async def unpack_archive(self, filename, extract_dir=None, format=None):

        def _unpack_archive(_filename, _extract_dir, _format):
            # imported function validates correctness/existence of archive and directories itself
            unpack_archive(filename=_filename, extract_dir=_extract_dir, format=_format)

        result = await self._loop.run_in_executor(self._pool, _unpack_archive,
                                                  filename, extract_dir, format)
