import asyncio
from datetime import datetime
from time import sleep
import sys

if __name__ == "__main__":
    # Add "csm" module at top
    sys.path.append("../../../../..") # Adds higher directory to python modules path.

from csm.core.data.db.db_provider import (DbStorageProvider, DbDriverConfig,
                                          DbDriverProvider, DbModelConfig, DbConfig)
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
          'resolved': 1,
          'acknowledged': 0,
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
          'resolved': 0,
          'acknowledged': 0,
          'severity': 1,
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }


async def example():
    conf = DbConfig({
        "drivers": {
            "es_db": {
                "import_path": "csm.core.data.db.elasticsearch_db.driver.ElasticSearchDriver",
                "config": {
                    "hosts": ["localhost"],
                    "login": "",
                    "password": ""
                }
            }
        },
        "models": [
            {
                "import_path": "csm.core.blogic.models.alerts.AlertExample",
                "driver": "es_db",
                "config": {
                    "es_db":
                        {
                            "index": "alert"
                        }
                }
            }]
    })

    driver_provider = DbDriverProvider(conf.drivers)
    db = DbStorageProvider(driver_provider, conf.models)

    alert1 = AlertExample(ALERT1)
    alert2 = AlertExample(ALERT2)

    await db(AlertExample).store(alert1)
    await db(AlertExample).store(alert2)

    filter = And(Compare(AlertExample.id, "=", 22), And(Compare(AlertExample.status, "=", "Success"),
                                                 Compare(AlertExample.id, ">", 1)))
    query = Query().filter_by(filter).order_by(AlertExample.id, SortOrder.DESC)
    res = await db(AlertExample).get(query)
    print(f"Get by query: {[alert.to_primitive() for alert in res]}")

    _id = 2
    res = await db(AlertExample).get_by_id(_id)
    if res is not None:
        print(f"Get by id = {_id}: {res.to_primitive()}")

    filter_obj = Or(Compare(AlertExample.id, "=", 1), Compare(AlertExample.id, "=", 2), Compare(AlertExample.id, "=", 22))
    res = await db(AlertExample).count(filter_obj)
    print(f"Count by filter: {res}")

    res = await db(AlertExample).delete(filter_obj)
    print(f"Deleted by filter: {res}")


if __name__ == "__main__":
    sys.path.append("../../../../..") # Adds higher directory to python modules path.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(example())
    loop.close()
