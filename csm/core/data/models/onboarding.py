#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          onboarding.py
 Description:       Onboarding service

 Creation Date:     12/12/2019
 Author:            Oleg Babin

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from enum import Enum
from schematics.types import StringType
from csm.core.blogic.models import CsmModel


ONBOARDING_PHASES = [
    'uninitialized',
    'management_network',
    'management_network_ipv4',
    'management_network_ipv6',
    'data_network',
    'data_network_ipv4',
    'data_network_ipv6',
    'dns',
    'date_time',
    'users',
    'users_local',
    'users_ldap',
    'notifications',
    'notifications_email',
    'notifications_syslog',
    's3_account',
    's3_iam_users',
    's3_buckets',
    'complete'
]


class OnboardingConfig(CsmModel):
    """
    Data model for Onboarding Config
    TODO: Should be part of the system config in the future
    """

    # Our current GenericDB implementation requires
    # a 'primary key' field for every data model
    _id = 'config_id'
    config_id = StringType(default='onboarding')

    phase = StringType(choices=ONBOARDING_PHASES,
                       default=ONBOARDING_PHASES[0])
