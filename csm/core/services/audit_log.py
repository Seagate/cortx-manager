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

import asyncio
import re
import time
import os
import tarfile
from datetime import datetime, timedelta, timezone
from cortx.utils.log import Log
from csm.common.services import Service, ApplicationService
from csm.common.queries import SortBy, SortOrder, QueryLimits, DateTimeRange
from csm.core.blogic import const
from cortx.utils.data.db.db_provider import (DataBaseProvider, GeneralConfig)
from cortx.utils.data.access.filters import Compare, And, Or
from cortx.utils.data.access import Query, SortOrder
from csm.core.blogic.models.audit_log import CsmAuditLogModel, S3AuditLogModel
from csm.common import queries
from schematics import Model
from csm.common.errors import CsmNotFoundError
from typing import Optional, Iterable
from csm.common.conf import Conf
from csm.common.process import SimpleProcess

# mapping of component with model, field for
# range queires and log format
COMPONENT_MODEL_MAPPING = { "csm":
                            { "model" : CsmAuditLogModel,
                              "field" : CsmAuditLogModel.timestamp,
                              "format" : "{message}"
                            },
                            "s3":
                            { "model" : S3AuditLogModel,
                              "field" : S3AuditLogModel.timestamp,
                              "format" : ("{bucket_owner} {bucket} {time}"
      "{remote_ip} {requester} {request_id} {operation} {key} {request_uri}"
      "{http_status} {error_code} {bytes_sent} {object_size} {total_time}"
      "{turn_around_time} {referrer} {user_agent} {version_id} {host_id}"
      "{signature_version} {cipher_suite} {authentication_type} {host_header}")
                            }
                          }
COMPONENT_NOT_FOUND = "no_audit_log_for_component"

class AuditLogManager():
    def __init__(self, storage: DataBaseProvider):
        self.db = storage

    def _prepare_filters(self, component, create_time_range: DateTimeRange):
        range_condition = []
        range_condition = self._prepare_time_range(
                  COMPONENT_MODEL_MAPPING[component]["field"], create_time_range)
        return And(*range_condition)

    def _prepare_time_range(self, field, time_range: DateTimeRange):
        db_conditions = []
        if time_range and time_range.start:
            db_conditions.append(Compare(field, '>=', time_range.start))
        if time_range and time_range.end:
            db_conditions.append(Compare(field, '<=', time_range.end))
        return db_conditions

    async def retrieve_by_range(self, component, limits,
                       time_range: DateTimeRange):
        query_filter = self._prepare_filters(component, time_range)
        query = Query().filter_by(query_filter)
        if limits and limits.offset:
            query = query.offset(limits.offset)

        if limits and limits.limit:
            query = query.limit(limits.limit)

        query = query.order_by(COMPONENT_MODEL_MAPPING[component]["field"], "desc")
        return await self.db(COMPONENT_MODEL_MAPPING[component]["model"]).get(query)

    async def count_by_range(self, component,
                       time_range: DateTimeRange) -> int:
        query_filter = self._prepare_filters(component, time_range)
        return await self.db(COMPONENT_MODEL_MAPPING[component]["model"]).count(query_filter)

class AuditService(ApplicationService):
    def __init__(self, audit_mngr: AuditLogManager):
        self.audit_mngr = audit_mngr

    def generate_audit_log_filename(self, component, start_time, end_time):
        """ generate audit log file name from time range"""
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, const.CLUSTER_ID_KEY)
        if not cluster_id:
            cluster_id = const.NA
        start_date = datetime.fromtimestamp(start_time).strftime('%d-%m-%Y')
        end_date = datetime.fromtimestamp(end_time).strftime('%d-%m-%Y')
        return (f'{component}.{start_date}.{end_date}.{cluster_id}')

    def get_date_range_from_duration(self, start_date, end_date):
        """ get date time range from given duration """
        tz = datetime.now(timezone.utc).astimezone().tzinfo
        start_date = datetime.fromtimestamp(start_date).replace(
                                          tzinfo=tz).isoformat()
        end_date = datetime.fromtimestamp(end_date).replace(
                                          tzinfo=tz).isoformat()
        return DateTimeRange(start_date, end_date)

    async def create_audit_log_file(self, file_name, component, time_range):
        """ create audit log file and comrpess to tar.gz """
        try:
            if not os.path.exists(const.AUDIT_LOG): os.makedirs(const.AUDIT_LOG)
            txt_file_name = f'{os.path.join(const.AUDIT_LOG, file_name)}.txt'
            tar_file_name = f'{os.path.join(const.AUDIT_LOG, file_name)}.tar.gz'
            count = await self.audit_mngr.count_by_range(component, time_range)
            file = open(txt_file_name, "w")
            query_limit = QueryLimits(const.MAX_RESULT_WINDOW, 0)
            audit_logs = await self.audit_mngr.retrieve_by_range(component,
                                                 query_limit, time_range)
            for log in audit_logs:
                file.write(COMPONENT_MODEL_MAPPING[component]["format"].
                                           format(**(log.to_primitive()))+"\n")
            file.close()
            with tarfile.open(tar_file_name, "w:gz") as tar:
                tar.add(txt_file_name, arcname=f'{file_name}.txt')
        except OSError as err:
            if err.errno != errno.EEXIST: raise

    async def get_by_range(self, component: str, start_time: str, end_time: str):
        """ fetch all records for given range from audit log """
        Log.logger.info(f"auditlogs for {component} from {start_time} to {end_time}")
        if not COMPONENT_MODEL_MAPPING.get(component, None):
            raise CsmNotFoundError("No audit logs for %s" % component,
                                                   COMPONENT_NOT_FOUND)

        time_range = self.get_date_range_from_duration(int(start_time), int(end_time))
        query_limit = QueryLimits(Conf.get(const.CSM_GLOBAL_INDEX,
                                                   "Log.max_result_window"), 0)
        audit_logs = await self.audit_mngr.retrieve_by_range(component,
                                                   query_limit, time_range)
        return [COMPONENT_MODEL_MAPPING[component]["format"].
                               format(**(log.to_primitive())) for log in audit_logs ]

    async def get_audit_log_zip(self, component: str, start_time: str, end_time: str):
        """ get zip file for all records from given range """
        Log.logger.info("get audit logs for given range ")
        if not COMPONENT_MODEL_MAPPING.get(component, None):
            raise CsmNotFoundError("No audit logs for %s" % component,
                                                   COMPONENT_NOT_FOUND)

        file_name = self.generate_audit_log_filename(component, start_time, end_time)
        time_range = self.get_date_range_from_duration(int(start_time), int(end_time))
        await self.create_audit_log_file(file_name, component, time_range)
        return f"{file_name}.tar.gz"
