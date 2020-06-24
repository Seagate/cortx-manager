#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          test_product_version.py
 description:       Product version test cases

 Creation Date:     06/19/2020
 Author:            Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio
import sys
import os
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.core.services.version import ProductVersionService

t = unittest.TestCase()

class MockProvisioner():
    
    async def get_current_version(self, *args, **kwargs):
        return {"NAME": "EES",
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
    sample_data = {"NAME": "EES",
            "VERSION": "1.0.0",
            "BUILD": "193",
            "RELEASE": "Cortx-1.0.0-12-rc7",
            "OS": "Red Hat Enterprise Linux Server release 7.7 (Maipo)",
            "DATETIME": "09-Jun-2020 05:57 UTC",
            "KERNEL": "3.10.0_1062.el7",
            "LUSTRE_VERSION": ""
            }

    response_data = loop.run_until_complete(product_version_service.get_current_version())
    assert 'VERSION' in response_data
    assert response_data == sample_data

test_list = [test_get_product_version]
