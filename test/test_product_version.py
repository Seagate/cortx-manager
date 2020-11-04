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

import asyncio
import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.core.services.version import ProductVersionService  # noqa: E402

t = unittest.TestCase()


class MockProvisioner():
    async def get_current_version(self, *args, **kwargs):
        return {"NAME": "CORTX",
                "VERSION": "1.0.0",
                "BUILD": "193",
                "RELEASE": "Cortx-1.0.0-12-rc7",
                "OS": "Red Hat Enterprise Linux Server release 7.7 (Maipo)",
                "DATETIME": "09-Jun-2020 05:57 UTC",
                "KERNEL": "3.10.0_1062.el7",
                "LUSTRE_VERSION": ""
                }


def init(args):
    provisioner = MockProvisioner()
    product_version_service = ProductVersionService(provisioner)
    loop = asyncio.get_event_loop()
    args['product_version_service'] = product_version_service
    args['loop'] = loop


def test_get_product_version(args):
    loop = args['loop']
    product_version_service = args.get('product_version_service')
    sample_data = {
        "NAME": "EES",
        "VERSION": "1.0.0",
        "BUILD": "193",
        "RELEASE": "Cortx-1.0.0-12-rc7",
        "OS": "Red Hat Enterprise Linux Server release 7.7 (Maipo)",
        "DATETIME": "09-Jun-2020 05:57 UTC",
        "KERNEL": "3.10.0_1062.el7",
        "LUSTRE_VERSION": ""}
    response_data = loop.run_until_complete(product_version_service.get_current_version())
    assert 'VERSION' in response_data
    assert response_data == sample_data


test_list = [test_get_product_version]
