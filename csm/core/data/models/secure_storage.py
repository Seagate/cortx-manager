"""
 ****************************************************************************
 Filename:          secure_storage.py
 Description:       Models for secure storage implementation upon Consul KVS

 Creation Date:     02/03/2020
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from schematics.types import StringType

from csm.core.blogic.models.base import CsmModel


class NamedEncryptedBytes(CsmModel):
    """
    Encrypted bytes model
    """

    _id = "name"

    name = StringType()
    data = StringType()

    @staticmethod
    def instantiate(name: str, data: str):
        """
        Creates an NamedEncryptedBytes instance
        """

        neb = NamedEncryptedBytes()
        neb.name = name
        neb.data = data
        return neb
