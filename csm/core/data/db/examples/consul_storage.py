#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          consul_storage.py
 _description:      Example of Consule usage

 Creation Date:     18/10/2019
 Author:            Dmitry Didenko

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio
from datetime import datetime

from csm.core.data.db.db_provider import DataBaseProvider, GeneralConfig
from csm.core.data.access.filters import Compare, And, Or
from csm.core.data.access import Query, SortOrder
from csm.core.blogic.models.alerts import AlertExample


ALERT1 = {'id': 22,
          'alert_uuid': 1,
          'status': "Success",
          'type': "Hardware",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Good",
          'health_recommendation': "Replace Disk",
          'location': "USA",
          'resolved': True,
          'acknowledged': True,
          'severity': 1,
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

ALERT2 = {'id': 23,
          'alert_uuid': 2,
          'status': "Failed",
          'type': "Hardware",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Good",
          'health_recommendation': "Replace Disk",
          'location': "India",
          'resolved': False,
          'acknowledged': False,
          'severity': 1,
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

ALERT3 = {'id': 24,
          'alert_uuid': 3,
          'status': "Failed",
          'type': "Software",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Bad",
          'health_recommendation': "Replace Disk",
          'location': "Russia",
          'resolved': True,
          'acknowledged': True,
          'severity': 1,
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

ALERT4 = {'id': 25,
          'alert_uuid': 4,
          'status': "Success",
          'type': "Software",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Greate",
          'health_recommendation': "Replace Unity",
          'location': "Russia",
          'resolved': False,
          'acknowledged': False,
          'severity': 1,
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }


async def example():
    conf = GeneralConfig({
        "databases": {
            "es_db": {
                "import_path": "ElasticSearchDB",
                "config": {
                    "host": "localhost",
                    "port": 9200,
                    "login": "",
                    "password": ""
                }
            },
            "consul_db":
                {
                    "import_path": "ConsulDB",
                    "config":
                        {
                            "host": "127.0.0.1",
                            "port": 8500,  # HTTP API Port
                            "login": "",
                            "password": ""
                        }
                }
        },
        "models": [
            {
                "import_path": "csm.core.blogic.models.alerts.AlertExample",
                "database": "consul_db",
                "config": {
                    "es_db": {
                        "collection": "alerts"
                    },
                    "consul_db": {
                        "collection": "alerts"
                    }
                }
            },
            # {
            #     "import_path": "Events",
            #     "driver": "consul_db",
            #     "config": {
            #         "consul_db": {
            #             "collection": "event"
            #         }
            #     }
            # }
        ]
    })

    db = DataBaseProvider(conf)

    alert1 = AlertExample(ALERT1)
    alert2 = AlertExample(ALERT2)
    alert3 = AlertExample(ALERT3)
    alert4 = AlertExample(ALERT4)

    await db(AlertExample).store(alert1)
    await db(AlertExample).store(alert2)
    await db(AlertExample).store(alert3)
    await db(AlertExample).store(alert4)

    res = await db(AlertExample)._get_all_raw()
    print([model for model in res])
    _id = 2
    res = await db(AlertExample).get_by_id(_id)
    if res is not None:
        print(f"Get by id = {_id}: {res.to_primitive()}")
    filter_obj = Or(And(Compare(AlertExample.id, ">=", 23),
                        Compare(AlertExample.status, "=", "Success")),
                    And(Compare(AlertExample.alert_uuid, "<=", 3),
                        Compare(AlertExample.status, "=", "Success")))

    query = Query().filter_by(filter_obj)
    res = await db(AlertExample).get(query)

    for model in res:
        print(f"Get by query ={model.to_primitive()}")

    query = Query().filter_by(filter_obj).order_by(AlertExample.location)
    res = await db(AlertExample).get(query)

    for model in res:
        print(f"Get by query with order_by ={model.to_primitive()}")

    count = await db(AlertExample).count(filter_obj)

    print(f"Count by filter = {count}")

    num = await db(AlertExample).delete(filter_obj)
    print(f"Deleted by filter={num}")

    await db(AlertExample).delete_by_id(4)

    count = await db(AlertExample).count()

    print(f"Remaining objects in consul = {count}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(example())
    loop.close()
