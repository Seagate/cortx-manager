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

from eos.utils.data.db.db_provider import DataBaseProvider
from csm.core.blogic.models.support_bundle import SupportBundleModel
from eos.utils.data.access import Query
from eos.utils.data.access.filters import Compare

class SupportBundleRepository:
    def __init__(self, storage: DataBaseProvider):
        self.db = storage

    async def retrieve_all(self, bundle_id) -> [SupportBundleModel]:
        query = Query().filter_by(Compare(SupportBundleModel.bundle_id, '=',
                                          bundle_id))
        return await self.db(SupportBundleModel).get(query)
