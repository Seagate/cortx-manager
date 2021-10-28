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


from urllib.parse import urlparse
import inspect, os, sys
from consul import Consul

from cortx.utils.kv_store.kv_store import KvStore as BaseStore
from cortx.utils.kv_store.kv_store_collection import ConsulKvPayload

class FileStore(BaseStore):
    _identifier = 'file'
    def __init__(self, store_loc, store_path, delim='>'):
        super(FileStore, self).__init__(store_loc, store_path, delim)
        if not os.path.exists(self._store_path):
            with open(self._store_path, 'w+') as f:
                pass

    def store(self, data):
        '''
        Store data to File
        '''
        s1 = f"{data['timestamp']} {data['component']} {data['user']} {data['remote_ip']} {data['path']}"
        with open(self._store_path, 'a') as f:
            f.write(str(s1))
            f.write("\n")

    def search(self, filter):
        '''
        Search data from File
        '''
        with open(self._store_path) as f:
            data = f.read()
        return data

class ConsulStore(BaseStore):
    _identifier = 'consul'
    def __init__(self, store_loc, store_path, delim='>'):
        super(ConsulStore,self).__init__(store_loc, store_path, delim)
        if store_loc:
            if ':' in store_loc:
                host, port = store_loc.split(':')
            else:
                host, port = store_loc, 8500
        else:
            host, port = '127.0.0.1', 8500
        self.c = Consul(host=host, port=port)
        self._payload = ConsulKvPayload(self.c, self._delim)
        self._consul_base = 'cortx/logs/auditlog/'

    def store(self,data):
        '''
        Store data to Consul
        '''
        self._payload._set(f"{self._consul_base}{data['component']}/{data['timestamp']}", str(data))

    def search(self, component):
        '''
        Search data from Consul
        '''
        data = self._payload.get_keys(self._consul_base+component)
        if data:
            return {each_data:self._payload.get(each_data) for each_data in data}

class LogStoreFactory:
    _stores = {}

    def __init__(self):
        """ Initializing LogStoreFactory """
        pass

    @staticmethod
    def get_instance(store_url: str, delim='>'):
        """ Obtain instance of KvStore for given file_type """

        url_spec = urlparse(store_url)
        store_type = url_spec.scheme
        store_loc = url_spec.netloc
        store_path = url_spec.path

        if store_url in LogStoreFactory._stores.keys():
            return LogStoreFactory._stores[store_url]

        storage = inspect.getmembers(sys.modules[__name__],inspect.isclass)
        for name, cls in storage:
            if hasattr(cls, '_identifier') and store_type == cls._identifier:
                LogStoreFactory._stores[store_url] = cls(store_loc, store_path,
                                                        delim)
                return LogStoreFactory._stores[store_url]
