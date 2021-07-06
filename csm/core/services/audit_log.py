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

import errno
import os
import tarfile
from datetime import datetime, timezone
from cortx.utils.log import Log
from csm.common.services import ApplicationService
from csm.common.queries import SortBy, QueryLimits, DateTimeRange
from csm.core.blogic import const
from cortx.utils.data.db.db_provider import DataBaseProvider
from cortx.utils.data.access.filters import Compare, And
from cortx.utils.data.access import Query, SortOrder
from csm.core.blogic.models.audit_log import CsmAuditLogModel, S3AuditLogModel
from csm.core.services.s3.utils import CsmS3ConfigurationFactory
from csm.plugins.cortx.s3 import S3Plugin
from csm.common.errors import CsmNotFoundError
from typing import Optional, Dict, List, Any
from cortx.utils.conf_store.conf_store import Conf

# mapping of component with model, field for
# range queires and log format
COMPONENT_MODEL_MAPPING = {
    "csm": {
        "model": CsmAuditLogModel,
        "field": CsmAuditLogModel.timestamp,
        "format": (
            "{timestamp} {user} {remote_ip} {forwarded_for_ip} {method} {path} {user_agent} "
            "{response_code} {request_id}"
        ),
    },
    "s3": {
        "model": S3AuditLogModel,
        "field": S3AuditLogModel.timestamp,
        "format": (
            "{bucket_owner} {bucket} {time}"
            "{remote_ip} {requester} {request_id} {operation} {key} {request_uri}"
            "{http_status} {error_code} {bytes_sent} {object_size} {total_time}"
            "{turn_around_time} {referrer} {user_agent} {version_id} {host_id}"
            "{signature_version} {cipher_suite} {authentication_type} {host_header}"
        ),
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

    async def retrieve_by_range(
        self, component, limits, time_range: DateTimeRange, sort: Optional[SortBy] = None
    ):
        query_filter = self._prepare_filters(component, time_range)
        query = Query().filter_by(query_filter)
        if limits and limits.offset:
            query = query.offset(limits.offset)

        if limits and limits.limit:
            query = query.limit(limits.limit)
        # TODO: A better solution for sorting in case of show logs and download logs
        if sort:
            query = query.order_by(
                getattr(COMPONENT_MODEL_MAPPING[component]["model"], sort.field), sort.order)
        else:
            query = query.order_by(COMPONENT_MODEL_MAPPING[component]["field"], "desc")
        return await self.db(COMPONENT_MODEL_MAPPING[component]["model"]).get(query)

    async def count_by_range(self, component, time_range: DateTimeRange) -> int:
        query_filter = self._prepare_filters(component, time_range)
        return await self.db(COMPONENT_MODEL_MAPPING[component]["model"]).count(query_filter)


class AuditService(ApplicationService):
    def __init__(self, audit_mngr: AuditLogManager, s3_plugin: S3Plugin):
        self.audit_mngr = audit_mngr
        self._s3_plugin = s3_plugin

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
        start_date = datetime.fromtimestamp(start_date).replace(tzinfo=tz).isoformat()
        end_date = datetime.fromtimestamp(end_date).replace(tzinfo=tz).isoformat()
        return DateTimeRange(start_date, end_date)

    # TODO this is obviously a stub; derive from `CsmAuditLogModel` if possible.
    async def get_csm_schema_info(self) -> List[Dict[str, Any]]:
        """
        Get CSM audit log schema.

        :returns: list of audit log field descriptors.
        """

        def is_visible(field_id):
            not_visible = ["remote_ip"]
            return field_id not in not_visible

        fields = [
            ["timestamp", "Timestamp", 201, {"type": "date"}],
            ["user", "User", 301],
            ["remote_ip", "Remote IP", 401],
            ["forwarded_for_ip", "Forwarded for IP", 501],
            ["method", "Method", 601],
            ["path", "Path", 701],
            ["user_agent", "User agent", 801],
            ["response_code", "Response code", 901],
            ["request_id", "Request ID", 1001],
            ["msg", "Message", 1101],
        ]

        descriptors = []
        for f in fields:
            item = {
                "field_id": f[0],
                "label": f[1],
                "display_id": f[2],
                "display": is_visible(f[0]),
                "sortable": True,
                "filterable": False,
            }
            try:
                item["value"] = f[3]
            except IndexError:
                pass
            descriptors.append(item)

        return descriptors

    async def get_s3_schema_info(self) -> List[Dict[str, Any]]:
        """
        Get S3 audit log schema.

        :returns: list of CSM audit log field descriptors.
        """

        connection_config = CsmS3ConfigurationFactory.get_s3_connection_config()
        schema = await self._s3_plugin.get_s3_audit_logs_schema(connection_config)
        return schema

    async def get_schema_info(self, component: str):
        COMPONENT_SCHEMA_MAPPING = {
            "csm": self.get_csm_schema_info(),
            "s3": self.get_s3_schema_info()
        }

        method = COMPONENT_SCHEMA_MAPPING.get(component, None)
        if method is None:
            raise CsmNotFoundError(f'No audit log schema for {component}', COMPONENT_NOT_FOUND)
        return await method

    async def create_audit_log_file(self, file_name, component, time_range):
        """ create audit log file and comrpess to tar.gz """
        try:
            if not os.path.exists(const.AUDIT_LOG):
                os.makedirs(const.AUDIT_LOG)
            txt_file_name = f'{os.path.join(const.AUDIT_LOG, file_name)}.txt'
            tar_file_name = f'{os.path.join(const.AUDIT_LOG, file_name)}.tar.gz'
            file = open(txt_file_name, "w")
            query_limit = QueryLimits(const.MAX_RESULT_WINDOW, 0)
            audit_logs = await self.audit_mngr.retrieve_by_range(component, query_limit, time_range)
            format_str = COMPONENT_MODEL_MAPPING[component]["format"]
            for log in audit_logs:
                file.write(format_str.format(**(log.to_primitive())) + "\n")
            file.close()
            with tarfile.open(tar_file_name, "w:gz") as tar:
                tar.add(txt_file_name, arcname=f'{file_name}.txt')
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise Exception(f"OS error occurred {err}")

    async def get_by_range(
        self,
        component: str,
        start_time: str,
        end_time: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_by: Optional[str] = None,
        direction: Optional[str] = None
    ) -> Dict:
        """ fetch all records for given range from audit log """
        Log.logger.info(f"auditlogs for {component} from {start_time} to {end_time}")
        if not COMPONENT_MODEL_MAPPING.get(component, None):
            raise CsmNotFoundError(f"No audit logs for {component}", COMPONENT_NOT_FOUND)

        time_range = self.get_date_range_from_duration(int(start_time), int(end_time))
        max_result_window = int(Conf.get(const.CSM_GLOBAL_INDEX, "Log>max_result_window"))
        effective_limit = min(limit, max_result_window) if limit is not None else max_result_window
        query_limit = None
        if offset is not None and offset > 1:
            query_limit = QueryLimits(effective_limit, (offset - 1) * effective_limit)
        else:
            query_limit = QueryLimits(effective_limit, 0)
        sort_options = SortBy(sort_by, SortOrder.ASC if direction == "asc" else SortOrder.DESC)
        audit_logs = await self.audit_mngr.retrieve_by_range(
            component, query_limit, time_range, sort_options)
        audit_logs_count = await self.audit_mngr.count_by_range(component, time_range)
        return {
            "total_records": min(audit_logs_count, max_result_window),
            "logs": [log.to_primitive() for log in audit_logs]
        }

    async def get_audit_log_zip(self, component: str, start_time: str, end_time: str):
        """ get zip file for all records from given range """
        Log.logger.info("get audit logs for given range ")
        if not COMPONENT_MODEL_MAPPING.get(component, None):
            raise CsmNotFoundError(f"No audit logs for {component}", COMPONENT_NOT_FOUND)

        file_name = self.generate_audit_log_filename(component, start_time, end_time)
        time_range = self.get_date_range_from_duration(int(start_time), int(end_time))
        await self.create_audit_log_file(file_name, component, time_range)
        return f"{file_name}.tar.gz"
