#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          elasticsearch_storage.py
 _description:      Example of Elasticsearch usage

 Creation Date:     06/10/2019
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
from time import sleep
import sys

if __name__ == "__main__":
    # Add "csm" module at top
    sys.path.append("../../../../..")  # Adds higher directory to python modules path.

from csm.core.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from eos.utils.db.filters import Compare, And, Or
from eos.utils.db import Query, SortOrder
from csm.core.blogic.models.alerts import AlertModel


ALERT1 = {'alert_uuid': 1,
          'status': "Success",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Good",
          'health_recommendation': "Replace Disk",
          'location': "USA",
          'resolved': True,
          'acknowledged': True,
          'severity': "Urgent",
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

ALERT2 = {'alert_uuid': 2,
          'status': "Failed",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Good",
          'health_recommendation': "Replace Disk",
          'location': "India",
          'resolved': False,
          'acknowledged': False,
          'severity': "Neutral",
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

ALERT3 = {'alert_uuid': 3,
          'status': "Failed",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Bad",
          'health_recommendation': "Replace Disk",
          'location': "Russia",
          'resolved': True,
          'acknowledged': True,
          'severity': "Normal",
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

ALERT4 = {'alert_uuid': 4,
          'status': "Success",
          'enclosure_id': 1,
          'module_name': "SSPL",
          'description': "Some Description",
          'health': "Greate",
          'health_recommendation': "Replace Unity",
          'location': "Russia",
          'resolved': False,
          'acknowledged': False,
          'severity': "Neutral",
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
            }
        },
        "models": [
            {
                "import_path": "csm.core.blogic.models.alerts.AlertModel",
                "database": "es_db",
                "config": {
                    "es_db":
                        {
                            "collection": "alert"
                        }
                }
            }]
    })

    db = DataBaseProvider(conf)

    alert1 = AlertModel(ALERT1)
    alert2 = AlertModel(ALERT2)
    alert3 = AlertModel(ALERT3)
    alert4 = AlertModel(ALERT4)

    await db(AlertModel).store(alert1)
    await db(AlertModel).store(alert2)
    await db(AlertModel).store(alert3)
    await db(AlertModel).store(alert4)

    res = await db(AlertModel).get(
        Query().filter_by(Compare(AlertModel.severity, "=", "Neutral")).order_by(
            AlertModel.severity,
            SortOrder.ASC))

    if res:
        for i, model in enumerate(res):
            print(f"Model {i}: {model.to_primitive()}")

    filter = And(Compare(AlertModel.primary_key, "=", 1),
                 And(Compare(AlertModel.status, "=", "Success"),
                     Compare(AlertModel.primary_key, ">", 1)))

    query = Query().filter_by(filter).order_by(AlertModel.primary_key, SortOrder.DESC)
    res = await db(AlertModel).get(query)
    print(f"Get by query: {[alert.to_primitive() for alert in res]}")

    to_update = {
        'location': "Russia",
        'alert_uuid': 22,
        'resolved': False,
        'created_time': datetime.now()
    }

    await db(AlertModel).update(filter, to_update)

    res = await db(AlertModel).get(query)
    print(f"Get by query after update: {[alert.to_primitive() for alert in res]}")

    _id = 2
    res = await db(AlertModel).get_by_id(_id)
    if res is not None:
        print(f"Get by id = {_id}: {res.to_primitive()}")

    await db(AlertModel).update_by_id(_id, to_update)

    updated_id = to_update['alert_uuid']
    res = await db(AlertModel).get_by_id(updated_id)
    if res is not None:
        print(f"Get by id after update = {_id}: {res.to_primitive()}")

    filter_obj = Or(Compare(AlertModel.primary_key, "=", 1), Compare(AlertModel.primary_key, "=", 2),
                    Compare(AlertModel.primary_key, "=", 4))
    res = await db(AlertModel).count(filter_obj)
    print(f"Count by filter: {res}")

    res = await db(AlertModel).delete(filter_obj)
    print(f"Deleted by filter: {res}")

    _id = 3
    is_deleted = await db(AlertModel).delete_by_id(_id)
    print(f"Object by id = {_id} was deleted: {is_deleted}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(example())
    loop.close()
