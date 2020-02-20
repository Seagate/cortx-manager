#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          file.py
 Description:       Service for file downloading/uploading

 Creation Date:     01/29/2020
 Author:            Artem Obruchnikov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


import os
import uuid
from abc import ABC
from enum import Enum
from typing import List
from shutil import copyfile
from contextlib import ContextDecorator

from csm.core.blogic import const
from csm.common.errors import CsmInternalError
from csm.core.blogic import const
from csm.common.log import Log


class FileType(Enum):
    """
    Enum for indicating group of files
    """
    SUPPORT_BUNDLE = 1
    ETC_CSM = 2
    AUDIT_LOG = 3


class DownloadFileEntity:
    """
    File representative for downloading it from server
    """

    def __init__(self, filename, path_to_file=None):
        self.filename = filename
        self.path_to_file = path_to_file


class DownloadFileManager:
    """
    Class for handling files download and upload
    """

    def __init__(self):
        self.directory_map = {
            FileType.SUPPORT_BUNDLE: const.DEFAULT_SUPPORT_BUNDLE_ROOT,
            FileType.ETC_CSM: const.CSM_ETC_DIR,
            # FileType.AUDIT_LOG: "PATH TO AUDIT LOG",
        }

    def get_file_response(self, ftype: FileType, filename) -> DownloadFileEntity:
        """
        Returns DownloadFileEntity by given file type and filename
        """

        directory = self.directory_map.get(ftype)
        if directory is None:
            raise CsmInternalError(
                f'Attempt to get unsupported directory - "{ftype}". ' + \
                f'Supported directories: {list(self.directory_map.keys())}')

        path_to_file = os.path.join(directory, filename)
        if not os.path.exists(path_to_file) or not os.path.isfile(path_to_file):
            raise CsmInternalError(f'Attempt to get non existing file')
        return DownloadFileEntity(filename, path_to_file)


class FileRef():
    def __init__(self, file_uuid):
        self.file_uuid = file_uuid
        self.cache_dir = const.CSM_TMP_FILE_CACHE_DIR

    def get_file_path(self) -> str:
        path_to_cached_file = os.path.join(self.cache_dir, self.file_uuid)
        if not os.path.exists(path_to_cached_file):
            raise CsmInternalError(
                'File was removed from cache. Ensure that you are calling ' + \
                'save_file in scope of FileCache context manager.')
        return path_to_cached_file

    def save_file(self, dir_to_save, filename, overwrite=False):
        path_to_cached_file = self.get_file_path()
        path_to_file_to_save = os.path.join(dir_to_save, filename)
        if os.path.exists(path_to_file_to_save) and not overwrite:
            raise CsmInternalError(
                f'File "{path_to_file_to_save}" already exists. Change ' + \
                '"overwrite" argument if you want to overwrite file')

        copyfile(path_to_cached_file, path_to_file_to_save)


class FileCache(ContextDecorator):
    def __init__(self):
        self.files_uuids = []
        self.cache_dir = const.CSM_TMP_FILE_CACHE_DIR

        self.current_writing_file_uuid = None
        self.current_writing_file_stream = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.current_writing_file_stream is not None:
            self.current_writing_file_stream.close()
            Log.error('Exiting FileCache context manager while file is writing')
        for file_uuid in self.files_uuids:
            path_to_file = os.path.join(self.cache_dir, file_uuid)
            if os.path.exists(path_to_file):
                os.remove(path_to_file)
            else:
                Log.error('Cached file was deleted out of scope of FileCache context manger')

    def cache_new_file(self):
        if self.current_writing_file_stream is not None:
            err_msg = 'Trying to open new file stream for caching while another file is writing'
            Log.error(err_msg)
            raise CsmInternalError(err_msg)

        file_uuid = uuid.uuid4().hex
        # TODO: check for existing file
        file_stream = open(os.path.join(self.cache_dir, file_uuid), 'w+b')

        self.files_uuids.append(file_uuid)
        self.current_writing_file_uuid = file_uuid
        self.current_writing_file_stream = file_stream

        return file_uuid

    def write_chunck(self, file_uuid, chunk):
        self.__check_file_uuid(file_uuid)
        if chunk != b'':
            self.current_writing_file_stream.write(chunk)
            return

        self.current_writing_file_stream.close()
        self.current_writing_file_stream = None
        self.current_writing_file_uuid = None

    def __check_file_uuid(self, file_uuid_to_check):
        if (self.current_writing_file_uuid is not None and
                file_uuid_to_check != self.current_writing_file_uuid):
            raise CsmInternalError('Trying to write file to cache while another file is writing')
