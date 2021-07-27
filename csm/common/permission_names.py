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

class Resource:
    ''' Resource Names '''

    ALERTS = 'alerts'
    STATS = 'stats'
    USERS = 'users'
    CAPACITY = 'capacity'
    SYSCONFIG = 'sysconfig'
    S3ACCOUNTS = 's3accounts'
    S3IAMUSERS = 's3iamusers'
    S3BUCKETS = 's3buckets'
    S3BUCKET_POLICY = 's3bucketpolicy'
    S3ACCESSKEYS = 's3accesskeys'
    AUDITLOG = 'auditlog'
    SYSTEM = 'system'
    MAINTENANCE = 'maintenance'
    NODE_REPLACEMENT = 'replace_node'
    PERMISSIONS = 'permissions'
    NOTIFICATION = 'notification'
    SECURITY = "security"
    LYVE_PILOT = 'lyve_pilot'
    HEALTH = 'health'
    CLUSTER_MANAGEMENT = 'cluster_management'


class Action:
    ''' Action Names '''

    LIST = 'list'
    READ = 'read'
    CREATE = 'create'
    DELETE = 'delete'
    UPDATE = 'update'
