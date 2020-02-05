"""
 ****************************************************************************
 Filename:          test_s3.py
 Description:       Test S3 server APIs.

 Creation Date:     11/14/2019
 Author:            Alexander Nogikh
                    Alexander Voronov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys,os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.log import Log
from csm.eos.plugins.s3 import S3ConnectionConfig, S3Plugin
from csm.eos.plugins.s3 import ExtendedIamAccount, IamAccountListResponse
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

async def is_udx_bucket(s3_client, bucket):
    # TODO: Ref: EOS-4272: This part of testcases will be added to the actual CSM
    #       code in future. Commiting this functionality as testcase.
    #       [test_disallow_list_udx_bucket, test_disallow_delete_udx_bucket]
        tag = await s3_client.get_bucket_tagging(bucket)
        if tag.get("udx") == "enabled":
            return True
        return False
    
async def _disallow_list_udx_bucket(s3_client):
    bucket_list = await s3_client.get_all_buckets()
    response_bucket_list = []
    response_bucket_list = [{"name": bucket.name} for bucket in bucket_list 
                            if not await is_udx_bucket(s3_client, bucket)]

    #Will cross verify if UDX enabled buket is listed or not
    for bucket in response_bucket_list:
        tag = await s3_client.get_bucket_tagging(bucket)
        if tag.get('udx') == 'enabled':
            raise TestFailed(f"UDX tag enabled bucket {bucket.name} still listed.")
        
async def _disallow_delete_udx_bucket(s3_client, bucket_name):
    
    for bucket in await s3_client.get_all_buckets():
        if bucket.name == bucket_name:
            if is_udx_bucket(s3_client, bucket):
                raise TestFailed(f"UDX tag enabled bucket {bucket_name} not" 
                                 "allowed to delete")
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
    iam_conf.host = "sati10b-m08.mero.colo.seagate.com"
    iam_conf.port = 9080

    delete_client = s3_plugin.get_iam_client(account.access_key_id, account.secret_key_id, iam_conf)

    loop.run_until_complete(_test_delete_account(delete_client, account))
    
def test_disallow_list_udx_bucket(args):
    """
    Testcase to verify disallowing listing of UDX bucket.
    """

    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']
    s3_conf = S3ConnectionConfig()
    s3_conf.host = args['S3']['host']
    s3_conf.port = 80
    s3_client = s3_plugin.get_s3_client(account.access_key_id, account.secret_key_id, s3_conf)
    loop.run_until_complete(_disallow_list_udx_bucket(s3_client))

def test_disallow_delete_udx_bucket(args):
    """
    Testcase to verify disallowing deleteing of UDX bucket.
    """

    loop = args['loop']
    s3_plugin = args['s3_plugin']
    account = args['s3_account']
    s3_conf = S3ConnectionConfig()
    s3_conf.host = args['S3']['host']
    s3_conf.port = 80
    s3_client = s3_plugin.get_s3_client(account.access_key_id, account.secret_key_id, s3_conf)
    bucket_name = "test_bucket-udx"
    loop.run_until_complete(_disallow_delete_udx_bucket(s3_client, bucket_name))

test_list = [test_create_account, test_create_list_delete_bucket, test_delete_account,
             test_disallow_list_udx_bucket, test_disallow_delete_udx_bucket]