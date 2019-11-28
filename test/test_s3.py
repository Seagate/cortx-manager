import asyncio
from csm.common.log import Log
from csm.eos.plugins.s3 import S3ConnectionConfig, S3Plugin
from csm.eos.plugins.s3 import ExtendedIamAccount, IamAccountListResponse

Log.init('test', '.')

# TODO: integrate the test into testing framework
if __name__ == '__main__':
    iam_conf = S3ConnectionConfig()
    iam_conf.host = "sati10b-m08.mero.colo.seagate.com"
    iam_conf.port = 9080

    s3_conf = S3ConnectionConfig()
    s3_conf.host = "sati10b-m08.mero.colo.seagate.com"
    s3_conf.port = 80

    pl = S3Plugin()
    client = pl.get_iam_client("sgiamadmin", "ldapadmin", iam_conf)
    loop = asyncio.get_event_loop()

    async def _test_create_account():
        account = await client.create_account('test_s3_acc', 'test_s3_acc@test.com')
        if not isinstance(account, ExtendedIamAccount):
            print("Account creation failed: " + repr(account))
            return

        account_list = await client.list_accounts()
        if not isinstance(account_list, IamAccountListResponse):
            print("Account list fetching failed: " + repr(account))
            return

        if not any(x.account_name == account.account_name for x in account_list.iam_accounts):
            print("There is no account in the account list")
            return

        print("Test account has been created successfully")
        return account

    async def _test_create_list_delete_bucket(account: ExtendedIamAccount):
        s3cli = pl.get_s3_client(account.access_key_id, account.secret_key_id, s3_conf)
        bucket_name = 's3plugintest'

        bucket = await s3cli.create_bucket(bucket_name)
        if bucket is None:
            print("Cannot create bucket ", bucket_name)
            return

        bucket_list = await s3cli.get_all_buckets()
        if bucket_list is None:
            print("Cannot get the bucket list")
            return

        if not any(b.name == bucket_name for b in bucket_list):
            print("The bucket has not been created")
            return

        await s3cli.delete_bucket(bucket)

        bucket_list = await s3cli.get_all_buckets()
        if bucket_list is None:
            print("Cannot get the bucket list")
            return

        if any(b.name == bucket_name for b in bucket_list):
            print("The bucket has not been deleted")
            return

        print("Bucket create/list/delete done successfully")

    async def _test_delete_account(account: ExtendedIamAccount):
        delete_client = pl.get_iam_client(account.access_key_id, account.secret_key_id, iam_conf)
        result = await delete_client.delete_account(account.account_name)

        if not (isinstance(result, bool) and result):
            print("Cannot delete the account")
        print("Test account has been deleted successfully")

    account = loop.run_until_complete(_test_create_account())
    loop.run_until_complete(_test_create_list_delete_bucket(account))
    loop.run_until_complete(_test_delete_account(account))
