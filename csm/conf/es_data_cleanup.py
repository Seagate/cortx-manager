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

from datetime import datetime, timedelta
import requests
import io
import argparse
import traceback
import sys
import os
import pathlib
import json
from cortx.utils.cleanup.es_data_cleanup import esCleanup

if __name__ == '__main__':

    try:
        argParser = argparse.ArgumentParser(
            usage = "%(prog)s [-h] [-d] [-n] [-i] [-f]",
            formatter_class = argparse.RawDescriptionHelpFormatter)
        argParser.add_argument("-d", type=int, default=90,
                help="days to keep data")
        argParser.add_argument("-n", type=str, default="localhost:9200",
                help="address:port of elasticsearch service")
        argParser.add_argument("-f", type=str, default="timestamp",
                help="field of index of elasticsearch service")
        argParser.add_argument("-i", nargs='+', default=[],
                help="index of elasticsearch")
        args = argParser.parse_args()
        # Pass arguments to worker function
        # remove data older than given number of days
        es = esCleanup("es_data_cleanup", "/var/log/seagate/common/")
        es.remove_old_data_from_indexes(args.d, args.n, args.i, args.f)
    except Exception as e:
        print(e, traceback.format_exc())
