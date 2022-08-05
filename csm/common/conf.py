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
from csm.common.payload import Payload
from csm.common.errors import CsmError, InvalidRequest
from cortx.utils.log import Log
from cortx.utils.security.cipher import Cipher, CipherInvalidToken


class ClusterIdFetchError(InvalidRequest):
    pass


class Conf:
    """Represent conf file - singleton."""

    _payloads = {}

    @staticmethod
    def init():
        """Initialize data from conf file."""
        pass

    @staticmethod
    def load(index, doc, force=False):
        if not os.path.isfile(doc):
            raise CsmError(-1, f'File {doc} does not exist')
        if index in Conf._payloads:
            if not force:
                raise Exception(f'index {index} is already loaded')
            Conf.save(index)
        Conf._payloads[index] = Payload(doc)

    @staticmethod
    def get(index, key, default_val=None):
        """Obtain value for the given key."""
        return Conf._payloads[index].get(key) \
            if default_val is None else default_val

    @staticmethod
    def set(index, key, val):
        """Set the value into the conf for the given key."""
        Conf._payloads[index].set(key, val)

    @staticmethod
    def delete(index, key):
        """
        Delete an entry from the configuration according to its key.

        :param key: key to be deleted.
        :return: deleted value.
        """
        return Conf._payloads[index].pop(key, None)

    @staticmethod
    def save(index=None):
        indexes = [x for x in Conf._payloads] if index is None else [index]
        for index in indexes:
            Conf._payloads[index].dump()


class ConfSection:
    """Represents sub-section of config file."""

    def __init__(self, from_dict: dict):
        """
        Initialize ConfSection by dictionary object.

        :param dict from_dict: base dictionary to create object from its keys and values.
        """
        for key, value in from_dict.items():
            if isinstance(value, dict):
                setattr(self, key, ConfSection(value))
            else:
                setattr(self, key, value)


class DebugConf:
    """
    Class which simplifies work with debug settings in debug mode.

    Make easy check whether debug-mode is enabled and requested option is set
    to desired value.
    """

    def __init__(self, debug_settings: ConfSection):
        """Initialize debug configuration instance by debug settings."""
        self._debug_settings = debug_settings

    def __getattr__(self, attr):
        """Redirect object's attributes to debug_settings."""
        return getattr(self._debug_settings, attr)

    @property
    def http_enabled(self):
        """Validate if debug mode is enabled and HTTP is chosen."""
        return self._debug_settings.enabled == 'true' \
            and self._debug_settings.http_enabled == 'true'


class Security:

    @staticmethod
    def decrypt(secret, private_key, decryption_key) -> str:
        """
        Utility method to decrypt a secret.

        Args:
            secret (str): Secret string to be decrypted.
            private_key (str): Private Key.
            decryption_key (str): Decryption Key.

        Raises:
            CipherInvalidToken: In case of decryption failure.

        Returns:
            str: Decrypted secret string.
        """
        try:
            cipher_key = Cipher.generate_key(private_key, decryption_key)
            decrypted_value = Cipher.decrypt(cipher_key,
                                                secret.encode("utf-8"))
            return decrypted_value.decode('utf-8')
        except CipherInvalidToken as error:
            Log.error(f"Decryption failed: {error}")
            raise CipherInvalidToken(f"Secret decryption Failed. {error}")
