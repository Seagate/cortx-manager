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
from enum import Enum

from csm.core.blogic import const
from csm.common.errors import CsmInternalError


class FileEntity:
    def __init__(self, filename, path_to_file):
        self.filename = filename
        self.path_to_file = path_to_file


class FileType(Enum):
    SUPPORT_BUNDLE = 1
    AUDIT_LOG = 2


class NetworkFileManager:

    def __init__(self):
        self.directory_map = {
            FileType.SUPPORT_BUNDLE: const.DEFAULT_SUPPORT_BUNDLE_ROOT,
            # FileType.AUDIT_LOG: "PATH TO AUDIT LOG",
        }

    def get_file_response(self, ftype: FileType, filename) -> FileEntity:
        "Returns FileEntity by given file type and filename"

        directory = self.directory_map.get(ftype)
        if directory is None:
            raise CsmInternalError(
                f'Attempt to get unsupported directory - "{ftype}". Supported directories: {list(self.directory_map.keys())}')
        path_to_file = os.path.join(directory, filename)
        if not os.path.exists(path_to_file) or not os.path.isfile(path_to_file):
            raise CsmInternalError(f'Attempt to get non existing file')
        return FileEntity(filename, path_to_file)

    def upload_file(self):
        raise CsmInternalError(f'Not implemented')
