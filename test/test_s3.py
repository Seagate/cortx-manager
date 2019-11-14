import asyncio
from csm.common.log import Log
from csm.eos.plugins.s3 import IamConnectionConfig, S3Plugin
from csm.eos.plugins.s3 import ExtendedIamAccount, IamAccountListResponse

Log.init('test', '.')

if __name__ == '__main__':
    config = IamConnectionConfig()
    config.host = "sati10b-m08.mero.colo.seagate.com"
    config.port = 9080

    pl = S3Plugin()
    client = pl.get_client("sgiamadmin", "ldapadmin", config)
    loop = asyncio.get_event_loop()

    async def _test_account_management():
        account = await client.create_account('test_account', 'test_email@test.com')
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

        delete_client = pl.get_client(account.access_key_id, account.secret_key_id, config)
        result = await delete_client.delete_account(account.account_name)

        if isinstance(result, bool) and result:
            print("Test is completed!")
        else:
            print("Cannot delete the account")

    loop.run_until_complete(_test_account_management())
