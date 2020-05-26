#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          conf.py
 Description:       Contains the configuration handling for CSM

 Creation Date:     31/05/2018
 Author:            Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
from eos.utils.log import Log
from csm.common.payload import *
from csm.common.errors import CsmError, InvalidRequest
from csm.core.blogic import const
from csm.common.process import SimpleProcess
from eos.utils.security.cipher import Cipher, CipherInvalidToken

class ClusterIdFetchError(InvalidRequest):
    pass

class Conf:
    ''' Represents conf file - singleton '''
    _payloads = {}

    @staticmethod
    def init():
        ''' Initializes data from conf file '''
        pass

    @staticmethod
    def load(index, doc, force=False):
        if not os.path.isfile('%s' %doc):
            raise CsmError(-1, 'File %s does not exist' %doc)
        if index in Conf._payloads.keys():
            if force == False:
                raise Exception('index %s is already loaded')
            Conf.save(index)
        Conf._payloads[index] = Payload(doc)

    @staticmethod
    def get(index, key, default_val=None):
        ''' Obtain value for the given key '''
        return Conf._payloads[index].get(key) \
            if default_val is None else default_val

    @staticmethod
    def set(index, key, val):
        ''' Sets the value into the conf for the given key '''
        Conf._payloads[index].set(key, val)

    @staticmethod
    def save(index=None):
        indexes = [x for x in Conf._payloads.keys()] if index is None else [index]
        for index in indexes:
            Conf._payloads[index].dump()

    @staticmethod
    def decrypt_conf():
        """
        THis Method Will Decrypt all the Passwords in Config and Will Load the Same in CSM.
        :return:
        """
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY)
        if not cluster_id:
            raise ClusterIdFetchError("failed to get cluster id.")
        for each_key in const.DECRYPTION_KEYS:
            cipher_key = Cipher.generate_key(cluster_id,
                                             const.DECRYPTION_KEYS[each_key])
            encrypted_value = Conf.get(const.CSM_GLOBAL_INDEX, each_key)
            try:
                decrypted_value = Cipher.decrypt(cipher_key,
                                                 encrypted_value.encode("utf-8"))
                Conf.set(const.CSM_GLOBAL_INDEX, each_key,
                        decrypted_value.decode("utf-8"))
            except CipherInvalidToken as error:
                raise CipherInvalidToken(f"Decryption for {each_key} Failed. {error}")

class ConfSection:
    """Represents sub-section of config file"""

    def __init__(self, from_dict: dict):
        """
        Initialize ConfSection by dictionary object

        :param dict from_dict: base dictionary to create object from its keys and values
        """
        for key, value in from_dict.items():
            if isinstance(value, dict):
                setattr(self, key, ConfSection(value))
            else:
                setattr(self, key, value)


class DebugConf:
    """
    Class which simplifies work with debug settings in debug mode:

    make easy check whether debug-mode is enabled and requested option is set
    to desired value
    """

    def __init__(self, debug_settings: ConfSection):
        """
        Initialize debug configuration instance by debug settings

        """
        self._debug_settings = debug_settings

    def __getattr__(self, attr):
        return getattr(self._debug_settings, attr)

    @property
    def http_enabled(self):
        """
        Validates if debug mode is enabled and HTTP is chosen
        """
        return self._debug_settings.enabled and self._debug_settings.http_enabled
