"""
 ****************************************************************************
 Filename:          utils.py
 Description:       Utilities common for all services working with S3

 Creation Date:     03/02/2020
 Author:            Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.core.blogic import const
from csm.common.conf import Conf
from csm.common.log import Log
from csm.core.data.models.s3 import S3ConnectionConfig
from csm.plugins.eos.s3 import IamClient


class CsmS3ConfigurationFactory:
    """
    Factory for the most common CSM S3 connections configurations
    """

    @staticmethod
    def get_iam_connection_config():
        """
        Creates a configuration for S3 IAM connection
        """

        iam_connection_config = S3ConnectionConfig()
        iam_connection_config.host = Conf.get(
            const.CSM_GLOBAL_INDEX, const.S3_HOST)
        iam_connection_config.port = Conf.get(
            const.CSM_GLOBAL_INDEX, const.S3_IAM_PORT)
        iam_connection_config.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX,
                                                         const.S3_MAX_RETRIES_NUM)
        return iam_connection_config

    @staticmethod
    def get_s3_connection_config():
        """
        Creates a configuration for S3 connection
        """

        Log.debug("Get s3 connection config")
        s3_connection_config = S3ConnectionConfig()
        s3_connection_config.host = Conf.get(const.CSM_GLOBAL_INDEX, const.S3_HOST)
        s3_connection_config.port = Conf.get(
            const.CSM_GLOBAL_INDEX, const.S3_PORT)
        s3_connection_config.max_retries_num = Conf.get(const.CSM_GLOBAL_INDEX,
                                                        const.S3_MAX_RETRIES_NUM)
        return s3_connection_config


class IamRootClient(IamClient):
    """
    IAM client with the root privileges
    """

    def __init__(self):
        ldap_login = Conf.get(const.CSM_GLOBAL_INDEX, const.S3_LDAP_LOGIN)
        # TODO: Password should be taken as input and not read from conf file directly.
        ldap_password = Conf.get(const.CSM_GLOBAL_INDEX, const.S3_LDAP_PASSWORD)
        iam_conf = CsmS3ConfigurationFactory.get_iam_connection_config()
        super().__init__(ldap_login, ldap_password, iam_conf)
