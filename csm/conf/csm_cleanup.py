#!/usr/bin/env python3

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

# Script will delete old indexes in elasticsearch
#
# days parameter - how many days before current date will be listed for deletion
#                  0 - means delete all even today's data
# host parameter - address and port of elasticsearch server
#
# config - change default parameters in __main__
#
# Use -h option to show help

from datetime import datetime, timedelta
import requests
import io
import argparse
import traceback
import sys
import os
import pathlib

index_field_map = {
    "alerts" : "created_time",
    "alerts-history" : "created_time",
    "csmauditlog" : "timestamp",
    "s3-rsys-index" : "timestamp"
}

# Search outdated indexes in es reply and generate list of outdated indexes
def filter_out_old_indexes(date_before, indexes):
    index_start = indexes.find('index')
    uuid_start = indexes.find('uuid')
    l = []
    for line in io.StringIO(indexes):
        if 'statsd' in line:
            l_index = line[index_start:uuid_start].rstrip()
            l_date = l_index.split('-',1)[1]
            if (l_date <= date_before):
                l.append(l_index)
    return l

# Remove indexes of es db at address:port arg_n which are older than arg_d days
# use arg_e option set to True to debug (don't delete but only show commands)
def remove_old_indexes(es, arg_d, arg_n, arg_e):
    if arg_n:
        host = arg_n
    days = arg_d
    Log.debug(f'Will keep indexes for [{days}] days')
    date_N_days_ago = datetime.now() - timedelta(days=days)
    date_dago = str(datetime.strftime(date_N_days_ago, '%Y.%m.%d'))
    Log.debug(f'Will remove all indexes earlier than [{date_dago}]')
    try:
        response = requests.get(f'http://{host}/_cat/indices?v')
    except Exception as e:
        Log.error(f'ERROR: can not connect to {host}, exiting')
        return

    if response.status_code == 200:
        Log.debug(f"Indexes list received from [{host}] successfully")
        l = filter_out_old_indexes(date_dago, response.text)
        i=0
        r=0
        if l:
            for k in l:
                i=i+1
                if arg_e:
                    Log.debug(f'curl -XDELETE http://{host}/{k}')
                else:
                    es.remove_by_index(host, k)
                    r=r+1;
            if i==r:
                Log.info(f"Successfully removed {r} old indexes")
        else:
            Log.debug("Nothing to remove")

def clean_indexes(es, no_of_days, host_port):
    for index, timestamp_field in index_field_map.items():
        Log.debug(f"Removing data for old index:{index} for {no_of_days} days.")
        es.remove_old_data_from_indexes(no_of_days, host_port, [index], timestamp_field)
    remove_old_indexes(es, no_of_days, host_port, args.emulate)

def parse_dir_usage():
    try:
        res = StorageInfo.get_dir_usage(dir_path="/var/log/elasticsearch/", unit="M")
        es_storage = int(res[0].decode("utf-8").split('\t')[0].split('M')[0])
        Log.debug(f"ES storage:{es_storage}")
        return es_storage
    except Exception as e:
        Log.error(f"Error in processing du cmd: {e}")
        raise Exception(f"Error in processing du cmd: {e}")

def parse_fs_usage():
    try:
        cmd_data = StorageInfo.get_fs_usage(fs="/var/log", unit="M")
        storage_info = cmd_data[0].decode('utf-8').split('\n').pop(1).split(' ')
        result = [ele for ele in storage_info if len(ele)>0]
        var_log_storage = int(result[1].split('M')[0])
        var_log_usage_percent = int(result[4].split('%')[0])
        Log.debug(f"/var/log storage:{var_log_storage}, /var/log usage percent:{var_log_usage_percent}")
        return var_log_storage, var_log_usage_percent
    except Exception as e:
        Log.error(f"Error in processing df cmd: {e}")
        raise Exception(f"Error in processing df cmd: {e}")

def process_es_cleanup(args):
    # Pass arguments to worker function
    # remove data older than given number of days
    es = esCleanup(const.CSM_CLEANUP_LOG_FILE, const.CSM_LOG_PATH)
    days_to_keep_data = int(args.days_to_keep_data)
    clean_indexes(es, days_to_keep_data, args.host_port)
    var_log_storage, var_log_usage_percent = parse_fs_usage() #get current /var/log storage

    #calculate es_db_capp Eg. var_log_storage=8000MB es_storage_cap_percent=30%
    es_db_capping = (var_log_storage * int(args.es_storage_cap_percent)) / 100

    while var_log_usage_percent > int(args.var_log_cap_percent):
        # Break if current ES storage is less than ES capping OR
        # Break if no of days is less than or equal 5. Keep data for last 5days
        if (parse_dir_usage()<=es_db_capping) or (days_to_keep_data<=5):
            Log.debug("Breaking out.")
            break
        days_to_keep_data = days_to_keep_data-1
        clean_indexes(es, days_to_keep_data, args.host_port)
        var_log_storage, var_log_usage_percent = parse_fs_usage() #get current /var/log usage %

def add_cleanup_subcommand(main_parser):
    subparsers = main_parser.add_parser("es_cleanup", help='cleanup of audit log')
    subparsers.set_defaults(func=process_es_cleanup)
    subparsers.add_argument("-d","--days_to_keep_data", type=int, default=90,
                                            help="days to keep data")
    subparsers.add_argument("-c","--var_log_cap_percent", type=int, default=90,
                                            help="Capping for /var/log in percentage")
    subparsers.add_argument("-e","--es_storage_cap_percent", type=str, default=30,
                                            help="ES size in '%' of /var/log storage")
    subparsers.add_argument("-n","--host_port", type=str, default="localhost:9200",
                                            help="address:port of elasticsearch service")
    subparsers.add_argument("-m","--emulate", action='store_true',
                                            help="emulate, do not really delete indexes")

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..'))
    from cortx.utils.log import Log
    from cortx.utils.cleanup.es_data_cleanup import esCleanup
    from cortx.utils.conf_store.conf_store import Conf, ConfSection, DebugConf
    from csm.core.blogic import const
    from csm.common.payload import Yaml
    from csm.common.storage_usage import StorageInfo
    Conf.load(const.CSM_GLOBAL_INDEX, f"yaml://{const.CSM_CONF}")
    Log.init(const.CSM_CLEANUP_LOG_FILE,
            backup_count=Conf.get(const.CSM_GLOBAL_INDEX, "Log>total_files"),
            file_size_in_mb=Conf.get(const.CSM_GLOBAL_INDEX, "Log>file_size"),
            level=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_level"),
            log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path"))
    try:
        argParser = argparse.ArgumentParser()
        subparsers = argParser.add_subparsers()
        add_cleanup_subcommand(subparsers)
        args = argParser.parse_args()
        args.func(args)
    except Exception as e:
        Log.error(e, traceback.format_exc())
