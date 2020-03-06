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

if __name__ == "__main__":
    # Add "csm" module at top
    import sys
    sys.path.append("../../../../..")  # Adds higher directory to python modules path.

from aiohttp import ClientConnectorError

# from csm.core.blogic.models import CsmUser
from csm.core.data.db.db_provider import DataBaseProvider, GeneralConfig
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
          'severity': 1,
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
          'severity': 1,
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
          'severity': 1,
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
          'severity': 1,
          'state': "Unknown",
          'extended_info': "No",
          'module_type': "FAN",
          'updated_time': datetime.now(),
          'created_time': datetime.now()
          }

USER1 = {
    "id": 1,
    "login": "Admin",
    "passwd": "Admin",
    "is_superuser": True,
    "disabled": False
}

USER2 = {
    "id": 2,
    "login": "NewUser",
    "passwd": "NewPassword",
    "is_superuser": False,
    "disabled": True
}


async def user_example():
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
                "import_path": "csm.core.blogic.models.alerts.AlertModel",
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
            {
                "import_path": "csm.core.blogic.models.users.CsmUser",
                "database": "consul_db",
                "config": {
                    "es_db": {
                        "collection": "user"
                    },
                    "consul_db": {
                        "collection": "user"
                    }
                }
            },
            {
                "import_path": "csm.core.blogic.models.users.Permissions",
                "database": "consul_db",
                "config": {
                    "es_db": {
                        "collection": "permissions"
                    },
                    "consul_db": {
                        "collection": "permissions"
                    }
                }
            }
        ]
    })

    async def list_all_users():
        _all_users = await db(CsmUser).get(Query().filter_by(Compare(CsmUser.id, ">=", 0)))
        for _user in _all_users:
            print(f"Get by query with order_by ={_user.to_primitive()}")
        print("*" * 20)

    db = DataBaseProvider(conf)

    user1 = CsmUser(USER1)
    user2 = CsmUser(USER2)

    await db(CsmUser).store(user1)
    await db(CsmUser).store(user2)

    await list_all_users()

    to_update = {
        "passwd": "NewPassword1234"
    }

    user1_id = USER1['id']
    user2_id = USER2['id']

    res = await db(CsmUser).update_by_id(user1_id, to_update)
    await list_all_users()

    res = await db(CsmUser).delete_by_id(user2_id)

    await list_all_users()


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
                "import_path": "csm.core.blogic.models.alerts.AlertModel",
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
            #     "import_path": "csm.core.blogic.models.users.CsmUser",
            #     "database": "consul_db",
            #     "config": {
            #         "es_db": {
            #             "collection": "user"
            #         },
            #         "consul_db": {
            #             "collection": "user"
            #         }
            #     }
            # },
            # {
            #     "import_path": "csm.core.blogic.models.users.Permissions",
            #     "database": "consul_db",
            #     "config": {
            #         "es_db": {
            #             "collection": "permissions"
            #         },
            #         "consul_db": {
            #             "collection": "permissions"
            #         }
            #     }
            # }
        ]
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

    limit = 1
    offset = 0
    for i in range(4):
        res = await db(AlertModel).get(Query().offset(offset).limit(limit))
        for model in res:
            print(f"Get by offset = {offset}, limit = {limit} : {model.to_primitive()}")
            offset += 1

    res = await db(AlertModel)._get_all_raw()
    print([model for model in res])

    _id = 2
    res = await db(AlertModel).get_by_id(_id)
    if res is not None:
        print(f"Get by id = {_id}: {res.to_primitive()}")

    to_update = {
        'state': "Good",
        'location': "USA"
    }

    await db(AlertModel).update_by_id(_id, to_update)

    res = await db(AlertModel).get_by_id(_id)
    if res is not None:
        print(f"Get by id after update = {_id}: {res.to_primitive()}")

    filter_obj = Or(Compare(AlertModel.status, "=", "Success"),
                    And(Compare(AlertModel.alert_uuid, "<=", 3),
                        Compare(AlertModel.status, "=", "Success")))

    query = Query().filter_by(filter_obj)
    res = await db(AlertModel).get(query)

    for model in res:
        print(f"Get by query ={model.to_primitive()}")

    await db(AlertModel).update(filter_obj, to_update)

    res = await db(AlertModel).get(query)

    for model in res:
        print(f"Get by query after update={model.to_primitive()}")

    query = Query().filter_by(filter_obj).order_by(AlertModel.location)
    res = await db(AlertModel).get(query)

    for model in res:
        print(f"Get by query with order_by ={model.to_primitive()}")

    count = await db(AlertModel).count(filter_obj)

    print(f"Count by filter = {count}")

    num = await db(AlertModel).delete(filter_obj)
    print(f"Deleted by filter={num}")

    _id = 2
    is_deleted = await db(AlertModel).delete_by_id(_id)
    print(f"Object by id = {_id} was deleted: {is_deleted}")

    count = await db(AlertModel).count()

    print(f"Remaining objects in consul = {count}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(example())
    # loop.run_until_complete(user_example())
    loop.close()
