#!/bin/python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

from datetime import datetime
from experiments.audit_logs.log_store_collection import LogStoreFactory

class AuditLogStore():
    '''
    Base class for Auditlog store
    '''

    def __init__(self, storage_url, component='audit'):
        self.storage_url = storage_url
        self.component = component
        self._log_store_instance = LogStoreFactory.get_instance(storage_url)

    @staticmethod
    def store():
        raise NotImplementedError

    @staticmethod
    def search():
        raise NotImplementedError

class CsmAuditLogStore(AuditLogStore):
    def __init__(self, storage_url, component='CSM'):
        super(CsmAuditLogStore,self).__init__(storage_url,component)

    def store(self, *args, **kwargs):
        '''
        Store auditlog
        '''
        kwargs["timestamp"] = str(datetime.now())
        kwargs["component"] = self.component
        self._log_store_instance.store(kwargs)

    def search(self):
        '''
        Fetch auditlog
        '''
        data = self._log_store_instance.search(self.component)
        print(data)

# Test File storage for audit logs
file_auditlog_example = CsmAuditLogStore('file:///tmp/auditlog.log')
file_auditlog_example.store(user="admin", remote_ip="127.0.0.1",method="POST",path="/api/v2/login")
file_auditlog_example.search()

# Test Consul storage for audit logs
consul_auditlog_example = CsmAuditLogStore('consul:///')
consul_auditlog_example.store(user="admin", remote_ip="127.0.0.1",method="POST",path="/api/v2/login")
consul_auditlog_example.search()