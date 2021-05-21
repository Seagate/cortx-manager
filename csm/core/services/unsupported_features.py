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

from csm.common.services import ApplicationService
from csm.core.blogic import const
from csm.common.payload import Json
from cortx.utils.product_features import unsupported_features
from cortx.utils.log import Log

class UnsupportedFeaturesService(ApplicationService):
    """
    Service for acessing appliance information
    """

    async def get_unsupported_features(self):
        """
        Fetches unsupported featuters and returns to the calling function.
        The component list is obtained from feature endpoint mapping and
        unsupported list is obtained for those components along with CSM.
        These unsupported feature list is returned as response
        """
        def get_component_list_from_features_endpoints():
            Log.info("Get Component List.")
            feature_endpoints = Json(
            const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
            component_list = [feature for v in feature_endpoints.values() for
                              feature in v.get(const.DEPENDENT_ON)]
            return list(set(component_list))
        
        components_list = get_component_list_from_features_endpoints()
        components_list.append(const.CSM)
        unsupported_features_list = []
        for component in components_list:
            Log.info(f"Fetch Unsupported Features for {component}.")
            unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
            unsupported = await unsupported_feature_instance.get_unsupported_features(
                component_name=component)
            for feature in unsupported:
                unsupported_features_list.append(
                    feature.get(const.FEATURE_NAME))
        unique_unsupported_features_list = list(set(unsupported_features_list))
        return {
            "unsupported_features": unique_unsupported_features_list
        }
            
