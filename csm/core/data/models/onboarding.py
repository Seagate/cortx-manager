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
