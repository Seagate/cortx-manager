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

import errno

from csm.common.errors import CsmError
from csm.core.blogic import const
from csm.core.providers.providers import EmailProvider


class ProviderFactory:
    """Factory for representing and instantiating providers"""
    providers = {
        const.EMAIL_CONFIGURATION: EmailProvider,
    }

    @staticmethod
    def get_provider(name, cluster):
        """Returns provider instance corresponding to given name"""
        if name not in ProviderFactory.providers:
            raise CsmError(errno.EINVAL, f'Provider {name} not loaded')
        return ProviderFactory.providers[name](cluster)
