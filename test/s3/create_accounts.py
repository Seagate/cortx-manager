import requests
import time
import argparse
import traceback
import sys
import os
import pathlib


class S3AccountCreation:
    def __init__(self, host_port, no_of_s3_account, no_of_iam_users, no_of_buckets, csm_username, csm_password):
        self._host_port = host_port
        self._no_of_s3_account = no_of_s3_account
        self._no_of_iam_users = no_of_iam_users
        self._no_of_buckets = no_of_buckets
        self._csm_username = csm_username
        self._csm_password = csm_password
        self._password = "Seagate@1"

    @staticmethod
    def login(host_port, username, password):
        url = f'http://{host_port}/api/v1/login'
        myobj = {'username': username, 'password': password}
        Log.debug(f"Login request payload {myobj}")
        res = requests.post(url, json = myobj)
        if res.status_code == 200:
            auth_token = res.headers.get("Authorization")
            Log.info(f"Auth token {auth_token}")
            return auth_token
        else:
            Log.error(res.text)
            raise Exception(res.text)

    def create_s3_account(self, auth_token):
        timestamp = int(round(time.time() * 1000))

        for i in range(1, self._no_of_s3_account + 1):
            account_name = f"s3account_{timestamp}_{i}"
            account_email = f"{account_name}@seagate.com"
            s3accountobj = {"account_name":account_name,"account_email":account_email,"password":self._password}
            headers = {'Authorization': auth_token}
            create_account_url = f'http://{self._host_port}/api/v1/s3_accounts'
            Log.debug(f"S3 account creation pauload: {s3accountobj}")
            res = requests.post(create_account_url, json = s3accountobj, headers= headers)
            if res.status_code == 401:
                auth_token = S3AccountCreation.login(self._host_port, self._csm_username, self._csm_password)
                headers = {'Authorization': auth_token}
                res = requests.post(create_account_url, json = s3accountobj, headers= headers)
            Log.info(f'S3 account creation response: {res.text}')

            s3_auth = S3AccountCreation.login(self._host_port, account_name, self._password)
            s3_headers = {'Authorization': s3_auth}
            for j in range(1, self._no_of_iam_users + 1):
                iamobj = {"path":"/","user_name":f"iam_{timestamp}_{j}","password": self._password, "require_reset":True}
                Log.debug(f"IAM user creation pauload: {iamobj}")
                create_iam_url = f'http://{self._host_port}/api/v1/iam_users'
                iam_res = requests.post(create_iam_url, json = iamobj, headers= s3_headers)
                Log.info(f'IAM user creation response: {iam_res.text}')

            for k in range(1, self._no_of_buckets + 1):
                bucketobj = {"bucket_name": f"bucket-{timestamp}-{i}-{k}"}
                create_bucket_url = f'http://{self._host_port}/api/v1/s3/bucket'
                Log.debug(f"Bucket creation pauload: {bucketobj}")
                bucket_res = requests.post(create_bucket_url, json = bucketobj, headers= s3_headers)
                Log.info(f'Bucket creation response: {bucket_res.text}')

def process_s3_sanity(args):
    create_account = S3AccountCreation(args.host_port, args.no_of_s3_account, args.no_of_iam_users, args.no_of_buckets, args.csm_username, args.csm_password)
    auth_token = S3AccountCreation.login(args.host_port, args.csm_username, args.csm_password)
    create_account.create_s3_account(auth_token)

def add_s3_sanity_subcommand(main_parser):
    subparsers = main_parser.add_parser("s3_sanity_test", help='Create Accounts')
    subparsers.set_defaults(func=process_s3_sanity)
    subparsers.add_argument("-n","--no_of_s3_account", type=int, default=1,
                                            help="Number of S3 accounts to be created")
    subparsers.add_argument("-i","--no_of_iam_users", type=int, default=1,
                                            help="Number of IAM users to be created")
    subparsers.add_argument("-s","--host_port", type=str, default="localhost:28101",
                                            help="address:port of CSM")
    subparsers.add_argument("-u","--csm_username", type=str,
                                            help="CSM username")
    subparsers.add_argument("-p","--csm_password", type=str,
                                            help="CSM password")
    subparsers.add_argument("-b","--no_of_buckets", type=int, default=1,
                                            help="Number of buckets to be created")

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    from cortx.utils.log import Log
    from cortx.utils.conf_store.conf_store import Conf
    from csm.core.blogic import const
    from csm.common.payload import Yaml

    Conf.load(const.CSM_GLOBAL_INDEX, f"yaml://{const.CSM_CONF}")
    Log.init(const.CSM_S3_SANITY_LOG_FILE,
            syslog_server=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_server"),
            syslog_port=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_port"),
            backup_count=Conf.get(const.CSM_GLOBAL_INDEX, "Log>total_files"),
            file_size_in_mb=Conf.get(const.CSM_GLOBAL_INDEX, "Log>file_size"),
            level=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_level"),
            log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path"))
    try:
        argParser = argparse.ArgumentParser()
        subparsers = argParser.add_subparsers()
        add_s3_sanity_subcommand(subparsers)
        args = argParser.parse_args()
        Log.debug(f"Args: {args}")
        if not args.csm_username and not args.csm_password:
            Log.error("Username and Password cannot be empty")
            raise Exception("Username and Password cannot be empty")
        args.func(args)
    except Exception as e:
        Log.error(e, traceback.format_exc())