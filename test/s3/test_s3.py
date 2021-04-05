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

import sys
import os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from cortx.utils.log import Log
from csm.plugins.cortx.s3 import S3ConnectionConfig, S3Plugin
from csm.plugins.cortx.s3 import ExtendedIamAccount, IamAccountListResponse
from csm.test.common import TestFailed

Log.init('test', '.')


async def _test_create_account(iam_client):
    account = await iam_client.create_account('csm_s3_test', 'csm_s3_test@test.com')
    if not isinstance(account, ExtendedIamAccount):
        raise TestFailed("Account creation failed: " + repr(account))
    account_list = await iam_client.list_accounts()
    if not isinstance(account_list, IamAccountListResponse):
        raise TestFailed("Account list fetching failed: " + repr(account))
    if not any(x.account_name == account.account_name for x in account_list.iam_accounts):
        raise TestFailed("There is no account in the account list")
    return account


async def _test_create_iam_user(iam_client):
    iam_user = await iam_client.create_user('csm_s3_iam_test')
    if hasattr(iam_user, "error_code"):
        raise TestFailed("IAM user creation failed: " + repr(iam_user))
    users_list = await iam_client.list_users()
    if hasattr(users_list, "error_code"):
        raise TestFailed("IAM users list fetching failed: " + repr(users_list))
    if not any(x.user_name == iam_user.user_name for x in users_list.iam_users):
        raise TestFailed("There is no created user in the users list")
    return iam_user


async def _test_create_list_delete_iam_access_keys(iam_client, iam_user):
    creds = await iam_client.create_user_access_key(user_name=iam_user.user_name)
    if hasattr(creds, "error_code"):
        raise TestFailed("IAM user access key creation failed: " + repr(creds))
    creds_list = await iam_client.list_user_access_keys(user_name=iam_user.user_name)
    if not any(x.access_key_id == creds.access_key_id for x in creds_list.access_keys):
        raise TestFailed("There is no created access key in the list")
    result = await iam_client.delete_user_access_key(creds.access_key_id,
                                                     user_name=iam_user.user_name)
    if not (isinstance(result, bool) and result):
        raise TestFailed("Cannot delete the IAM user credentials")


async def _test_delete_iam_user(iam_client, iam_user):
    result = await iam_client.delete_user(iam_user.user_name)

    if not (isinstance(result, bool) and result):
        raise TestFailed("Cannot delete the IAM user")


async def _test_create_list_delete_bucket(s3_client):
    bucket_name = 's3plugintest'

    bucket = await s3_client.create_bucket(bucket_name)
    if bucket is None:
        raise TestFailed("Cannot create bucket " + bucket_name)

    bucket_list = await s3_client.get_all_buckets()
    if bucket_list is None:
        raise TestFailed("Cannot get the bucket list")

    if not any(b.name == bucket_name for b in bucket_list):
        raise TestFailed("The bucket has not been created")

    await s3_client.delete_bucket(bucket)

    bucket_list = await s3_client.get_all_buckets()
    if bucket_list is None:
        raise TestFailed("Cannot get the bucket list")

    if any(b.name == bucket_name for b in bucket_list):
        raise TestFailed("The bucket has not been deleted")



async def _test_delete_account(iam_client, account: ExtendedIamAccount):
    result = await iam_client.delete_account(account.account_name)

    if not (isinstance(result, bool) and result):
        raise TestFailed("Cannot delete the account")



async def is_lyve_pilot_bucket(s3_client, bucket):
    tag = await s3_client.get_bucket_tagging(bucket)
    if tag.get("udx") == "enabled":
        return True
    return False


async def _disallow_list_lyve_pilot_bucket(s3_client):
    bucket_list = await s3_client.get_all_buckets()
    response_bucket_list = []
    response_bucket_list = [{"name": bucket.name} for bucket in bucket_list
                            if not await is_lyve_pilot_bucket(s3_client, bucket)]

    # Will cross verify if buckets enabled for Lyve Pilot are listed or not
    for bucket in response_bucket_list:
        tag = await s3_client.get_bucket_tagging(bucket)
        if tag.get('udx') == 'enabled':
            raise TestFailed(f"Bucket enabled for Lyve Pilot {bucket.name} still listed.")


async def _disallow_delete_lyve_pilot_bucket(s3_client, bucket_name):

    for bucket in await s3_client.get_all_buckets():
        if bucket.name == bucket_name:
            if is_lyve_pilot_bucket(s3_client, bucket):
                raise TestFailed(
                    f"Bucked enabled for Lyve Pilot {bucket_name} not allowed to delete")
            await s3_client.delete_bucket(bucket_name)


def init(args):
    s3_plugin = S3Plugin()
    loop = asyncio.get_event_loop()

    args['s3_plugin'] = s3_plugin
    args['loop'] = loop


def test_create_account(args):
    loop = args['loop']
    s3_plugin = args['s3_plugin']
    host = args['S3']['host']
    login = args['S3']['login']
    passwd = args['S3']['password']


    iam_conf = S3ConnectionConfig()
    iam_conf.host = host
    iam_conf.port = 9080

    iam_client = s3_plugin.get_iam_client(login, passwd, iam_conf)

    account = loop.run_until_complete(_test_create_account(iam_client))
    args['s3_account'] = account


def test_create_list_delete_bucket(args):
    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']

    s3_conf = S3ConnectionConfig()
    s3_conf.host = args['S3']['host']
    s3_conf.port = 80

    s3_client = s3_plugin.get_s3_client(account.access_key_id, account.secret_key_id, s3_conf)

    loop.run_until_complete(_test_create_list_delete_bucket(s3_client))


def test_delete_account(args):
    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']

    iam_conf = S3ConnectionConfig()
    iam_conf.host = args['S3']['host']
    iam_conf.port = 9080

    delete_client = s3_plugin.get_iam_client(account.access_key_id, account.secret_key_id, iam_conf)

    loop.run_until_complete(_test_delete_account(delete_client, account))


def test_create_iam_user(args):
    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']

    iam_conf = S3ConnectionConfig()
    iam_conf.host = args['S3']['host']
    iam_conf.port = 9080

    iam_cli = s3_plugin.get_iam_client(account.access_key_id, account.secret_key_id, iam_conf)

    iam_user = loop.run_until_complete(_test_create_iam_user(iam_cli))
    args['iam_user'] = iam_user
    args['iam_client'] = iam_cli


def test_create_list_delete_iam_user_credentials(args):
    loop = args['loop']
    iam_user = args['iam_user']
    iam_client = args['iam_client']

    loop.run_until_complete(_test_create_list_delete_iam_access_keys(iam_client, iam_user))


def test_delete_iam_user(args):
    loop = args['loop']
    iam_user = args['iam_user']
    iam_client = args['iam_client']

    loop.run_until_complete(_test_delete_iam_user(iam_client, iam_user))


def test_disallow_list_lyve_pilot_bucket(args):
    """
    Testcase to verify disallowing listing of Lyve Pilot bucket.
    """

    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']
    s3_conf = S3ConnectionConfig()
    s3_conf.host = args['S3']['host']
    s3_conf.port = 80
    s3_client = s3_plugin.get_s3_client(account.access_key_id, account.secret_key_id, s3_conf)
    loop.run_until_complete(_disallow_list_lyve_pilot_bucket(s3_client))


def test_disallow_delete_lyve_pilot_bucket(args):
    """
    Testcase to verify disallowing deleteing of Lyve Pilot bucket.
    """

    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']
    s3_conf = S3ConnectionConfig()
    s3_conf.host = args['S3']['host']
    s3_conf.port = 80
    s3_client = s3_plugin.get_s3_client(account.access_key_id, account.secret_key_id, s3_conf)
    bucket_name = "lyve_drive_test_bucket"
    loop.run_until_complete(_disallow_delete_lyve_pilot_bucket(s3_client, bucket_name))


test_list = [test_create_account,
             test_create_iam_user, test_create_list_delete_iam_user_credentials,
             test_delete_iam_user,
             test_create_list_delete_bucket,
             test_disallow_list_lyve_pilot_bucket, test_disallow_delete_lyve_pilot_bucket,
             test_delete_account]
