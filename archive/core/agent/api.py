# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
from csm.common.services import Service
# from csm.core.blogic.models.audit_log import CsmAuditLogModel
class AlertHttpNotifyService(Service):
    def __init__(self):
        super().__init__()
        self.unpublished_alerts = set()

    def push_unpublished(self):
        while self.unpublished_alerts:
            self.handle_alert()

    def handle_alert(self, alert):
        self.unpublished_alerts.add(alert)
        if CsmRestApi.push(alert):
            self.unpublished_alerts.discard(alert)


#Audit log function
# @staticmethod
# def generate_audit_log_string(request, **kwargs):
#     if (getattr(request, "session", None) is not None
#             and getattr(request.session, "credentials", None) is not None):
#         user = request.session.credentials.user_id
#     else:
#         user = None
#     remote_ip = request.remote
#     forwarded_for_ip = str(request.headers.get('X-Forwarded-For')).split(',', 2)[0].strip()
#     try:
#         ip_address(forwarded_for_ip)
#     except ValueError:
#         forwarded_for_ip = None
#     path = request.path
#     method = request.method
#     user_agent = request.headers.get('User-Agent')
#     entry = {
#         'user': user if user else "",
#         'remote_ip': remote_ip,
#         'forwarded_for_ip': forwarded_for_ip if forwarded_for_ip else "",
#         'method': method,
#         'path': path,
#         'user_agent': user_agent,
#         'response_code': kwargs.get("response_code", ""),
#         'request_id': kwargs.get("request_id", int(time.time())),
#         'payload': kwargs.get("payload", "")
#     }
#     return json.dumps(entry)