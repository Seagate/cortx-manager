#!/usr/bin/python3

"""
 ****************************************************************************
 Filename:          es_data_cleanup.py
 Description:       Remove old elasticsearch data from indexes helper script

 Creation Date:     03/03/2020
 Author:            Mazhar Inamdar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from datetime import datetime, timedelta
import requests
import io
import argparse
import traceback
import sys
import os
import pathlib
import json
from eos.utils.cleanup.es_data_cleanup import esCleanup

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
