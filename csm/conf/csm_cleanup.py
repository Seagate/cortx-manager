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

def process_stats(args):
    # Pass arguments to worker function
    es = esCleanup(const.CSM_CLEANUP_LOG_FILE, const.CSM_LOG_PATH)
    remove_old_indexes(es, args.d, args.n, args.e)

def process_auditlogs(args):
    # Pass arguments to worker function
    # remove data older than given number of days
    es = esCleanup(const.CSM_CLEANUP_LOG_FILE, const.CSM_LOG_PATH)
    es.remove_old_data_from_indexes(args.d, args.n, args.i, args.f)

def add_stats_subcommand(main_parser):
    subparsers = main_parser.add_parser("stats", help='cleanup of stats log')
    subparsers.set_defaults(func=process_stats)
    subparsers.add_argument("-d", type=int, default=90,
            help="days to keep data")
    subparsers.add_argument("-n", type=str, default="localhost:9200",
            help="address:port of elasticsearch service")
    subparsers.add_argument("-e", action='store_true',
            help="emulate, do not really delete indexes")

def add_auditlog_subcommand(main_parser):
    subparsers = main_parser.add_parser("auditlogs", help='cleanup of audit log')
    subparsers.set_defaults(func=process_auditlogs)
    subparsers.add_argument("-d", type=int, default=90,
            help="days to keep data")
    subparsers.add_argument("-n", type=str, default="localhost:9200",
            help="address:port of elasticsearch service")
    subparsers.add_argument("-f", type=str, default="timestamp",
            help="field of index of elasticsearch service")
    subparsers.add_argument("-i", nargs='+', default=[],
            help="index of elasticsearch")

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    from cortx.utils.log import Log
    from cortx.utils.cleanup.es_data_cleanup import esCleanup
    from csm.common.conf import Conf, ConfSection, DebugConf
    from csm.core.blogic import const
    from csm.common.payload import Yaml
    Conf.init()
    Conf.load(const.CSM_GLOBAL_INDEX, Yaml(const.CSM_CONF))
    Log.init(const.CSM_CLEANUP_LOG_FILE,
            syslog_server=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_server"),
            syslog_port=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_port"),
            backup_count=Conf.get(const.CSM_GLOBAL_INDEX, "Log.total_files"),
            file_size_in_mb=Conf.get(const.CSM_GLOBAL_INDEX, "Log.file_size"),
            level=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_level"),
            log_path=Conf.get(const.CSM_GLOBAL_INDEX, "Log.log_path"))
    try:
        argParser = argparse.ArgumentParser()
        subparsers = argParser.add_subparsers()
        add_auditlog_subcommand(subparsers)
        add_stats_subcommand(subparsers)
        args = argParser.parse_args()
        args.func(args)
    except Exception as e:
        Log.error(e, traceback.format_exc())
